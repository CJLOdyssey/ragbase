"""pgvector + pg_trgm hybrid vector store for RAG pipeline.

Schema (alembic p9g3n006): vector_chunks (id, session_id, run_id, text, tags,
embedding vector(1024), user_id, asset_id, metadata).

Retrieval is hybrid: HNSW cosine leg (pgvector) ‖ pg_trgm word-similarity leg
(GIN), fused with Reciprocal Rank Fusion (k=60) — the pattern from pgvector's
official hybrid_search/rrf.py example. user_id is a mandatory filter on every
search: chunks are isolated per owner, never leakable across users.
"""

import json
from collections.abc import Sequence
from typing import Any

from core.infra.logging_config import get_logger
from sqlalchemy import text

from rag.rag_chunking import Chunk
from rag.rag_embedding import EMBEDDING_DIM
from rag.rag_store_curation import CurationMixin, _vector_literal

logger = get_logger(__name__)

_RRF_K = 60
_LEXICAL_MIN_LEN = 3  # pg_trgm degenerates below a trigram's worth of chars


class PgVectorStore(CurationMixin):
    """PostgreSQL vector store with hybrid search and per-user isolation.

    Requires:
      CREATE EXTENSION IF NOT EXISTS vector;
      CREATE EXTENSION IF NOT EXISTS pg_trgm;
    """

    def __init__(self) -> None:
        self._initialized = False

    async def _ensure_table(self) -> None:
        if self._initialized:
            return
        from core.infra.database import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            try:
                await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            except Exception:
                logger.warning("pgvector extension not available — install it first")

            await session.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS vector_chunks (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        run_id TEXT,
                        text TEXT NOT NULL,
                        tags TEXT[] DEFAULT '{{}}',
                        embedding vector({EMBEDDING_DIM}),
                        user_id TEXT NOT NULL DEFAULT '',
                        asset_id TEXT,
                        metadata JSONB,
                        enabled BOOLEAN NOT NULL DEFAULT TRUE
                    )
                """
                )
            )

            try:
                await session.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_vector_chunks_embedding "
                        "ON vector_chunks USING hnsw (embedding vector_cosine_ops)"
                    )
                )
            except Exception:
                try:
                    await session.execute(
                        text(
                            "CREATE INDEX IF NOT EXISTS idx_vector_chunks_embedding "
                            "ON vector_chunks USING ivfflat (embedding vector_cosine_ops)"
                        )
                    )
                except Exception:
                    logger.warning("No vector index available — searches will be sequential")
            await session.commit()
        self._initialized = True

    async def add(self, chunks: list[Chunk], user_id: str) -> None:
        """Insert chunks with embeddings, tagged with their owning user.

        Chunk ids are content hashes (session-independent), so the same text
        re-ingested in a different session hits ON CONFLICT: session_id and
        run_id must follow the newest insert, or ``clear_session`` would leave
        an orphan row bound to a stale session.
        """
        if not chunks:
            return
        await self._ensure_table()

        from core.infra.database import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            for chunk in chunks:
                if not chunk.embedding:
                    continue
                emb_str = _vector_literal(chunk.embedding)
                metadata = chunk.metadata or {}
                await session.execute(
                    text(
                        """
                        INSERT INTO vector_chunks
                            (id, session_id, run_id, text, tags, embedding,
                             user_id, asset_id, metadata)
                        VALUES (:id, :sid, :rid, :text, :tags,
                                CAST(:emb AS vector), :uid, :aid, CAST(:meta AS jsonb))
                        ON CONFLICT (id) DO UPDATE
                        SET session_id = EXCLUDED.session_id,
                            run_id = EXCLUDED.run_id,
                            text = EXCLUDED.text,
                            tags = EXCLUDED.tags,
                            embedding = EXCLUDED.embedding,
                            user_id = EXCLUDED.user_id,
                            asset_id = EXCLUDED.asset_id,
                            metadata = EXCLUDED.metadata
                        """
                    ),
                    {
                        "id": chunk.id,
                        "sid": chunk.session_id,
                        "rid": chunk.run_id or "",
                        "text": chunk.text,
                        "tags": chunk.tags,
                        "emb": emb_str,
                        "uid": user_id,
                        "aid": metadata.get("asset_id"),
                        "meta": json.dumps(metadata, ensure_ascii=False),
                    },
                )
            await session.commit()
        logger.info("pgvector: stored %d chunks", len(chunks))

    async def search(
        self,
        query_embedding: list[float],
        query_text: str,
        user_id: str,
        session_id: str | None = None,
        tag_filter: list[str] | None = None,
        asset_ids: list[str] | None = None,
        top_k: int = 5,
        min_score: float | None = None,
        embed_model: str | None = None,
        embed_model_filter: bool = False,
        method: str = "hybrid",
    ) -> list[dict[str, Any]]:
        """Vector / lexical / hybrid search over the chunk store.

        method: 'hybrid' (default) fuses HNSW cosine ‖ pg_trgm legs via RRF;
        'semantic' runs the vector leg only; 'lexical' the trgm leg only.

        user_id is mandatory — chunks of other owners are never candidates.
        min_score (optional) drops vector-leg hits below a similarity floor —
        low-scoring chunks never enter the RRF fusion. The lexical leg is
        already bounded by the pg_trgm word_similarity_threshold (0.3).
        ``embed_model`` + ``embed_model_filter`` restrict candidates to one
        embedding cohort (NULL matches legacy chunks without the marker) so
        query vectors are only compared against same-space vectors.
        Returns list of {text, tags, session_id, run_id, asset_id, metadata,
        similarity, score}, ordered by RRF score descending.
        """
        await self._ensure_table()

        from core.infra.database import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            params: dict[str, Any] = {"uid": user_id}
            where_clauses = _scope_filters(
                params,
                session_id=session_id,
                tag_filter=tag_filter,
                asset_ids=asset_ids,
            )
            where_clauses += ["user_id = :uid", "enabled"]

            if embed_model_filter:
                if embed_model is None:
                    where_clauses.append("(metadata->>'embed_model') IS NULL")
                else:
                    where_clauses.append("metadata->>'embed_model' = :em")
                    params["em"] = embed_model

            where_sql = " AND ".join(where_clauses)

            emb_str = _vector_literal(query_embedding)

            legs: list[list[dict[str, Any]]] = []

            if method in ("hybrid", "semantic"):
                # Add min_score filter only for vector search
                vec_where = where_sql
                vec_params = {**params}
                if min_score is not None:
                    vec_where += " AND (1 - (embedding <=> CAST(:emb AS vector))) >= :min_score"
                    vec_params["min_score"] = min_score

                vec_rows = await session.execute(
                    text(
                        f"""
                        SELECT id, text, tags, session_id, run_id, asset_id, metadata,
                               1 - (embedding <=> CAST(:emb AS vector)) AS similarity
                        FROM vector_chunks
                        WHERE {vec_where}
                        ORDER BY embedding <=> CAST(:emb AS vector)
                        LIMIT :vec_k
                    """
                    ),
                    {**vec_params, "emb": emb_str, "vec_k": top_k * 5},
                )
                legs.append(_rows_to_dicts(vec_rows.fetchall()))

            if len(query_text.strip()) >= _LEXICAL_MIN_LEN and method in (
                "hybrid",
                "lexical",
            ):
                await session.execute(text("SET LOCAL pg_trgm.word_similarity_threshold = 0.3"))
                lex_rows = await session.execute(
                    text(
                        f"""
                        SELECT id, text, tags, session_id, run_id, asset_id, metadata,
                               word_similarity(:q, text) AS similarity
                        FROM vector_chunks
                        WHERE {where_sql} AND text <% :q
                        ORDER BY word_similarity(:q, text) DESC
                        LIMIT :lex_k
                    """
                    ),
                    {**params, "q": query_text.strip(), "lex_k": top_k * 5},
                )
                legs.append(_rows_to_dicts(lex_rows.fetchall()))

        if len(legs) == 1:
            # Single-leg method: order by similarity (RRF is meaningless with
            # one ranking); score mirrors similarity for downstream merging.
            leg = legs[0]
            for row in leg:
                row["score"] = row["similarity"]
            return sorted(leg, key=lambda r: r["score"], reverse=True)[:top_k]
        return _rrf_fuse(legs, top_k)

    async def embed_model_groups(
        self,
        user_id: str,
        session_id: str | None = None,
        tag_filter: list[str] | None = None,
        asset_ids: list[str] | None = None,
    ) -> list[str | None]:
        """Distinct embedding-model cohorts inside the candidate scope.

        Mirrors what indexing records in chunk metadata; NULL covers legacy
        chunks written before per-KB binding (session-message ingest too).
        """
        await self._ensure_table()
        from core.infra.database import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            params: dict[str, Any] = {"uid": user_id}
            where_clauses = _scope_filters(
                params,
                session_id=session_id,
                tag_filter=tag_filter,
                asset_ids=asset_ids,
            )
            where_clauses += ["user_id = :uid", "enabled"]
            rows = await session.execute(
                text(
                    f"""
                    SELECT DISTINCT metadata->>'embed_model' AS em
                    FROM vector_chunks
                    WHERE {" AND ".join(where_clauses)}
                """
                ),
                params,
            )
            return [r[0] for r in rows.fetchall()]

    async def clear_asset(self, asset_id: str) -> None:
        """Delete all chunks of an asset — used on asset delete and reindex."""
        await self.clear_assets([asset_id])

    async def clear_assets(self, asset_ids: list[str]) -> None:
        """Batch-delete chunks of multiple assets (e.g. KB-wide rebind purge)."""
        if not asset_ids:
            return
        await self._ensure_table()
        from core.infra.database import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            await session.execute(
                text("DELETE FROM vector_chunks WHERE asset_id = ANY(:aids)"),
                {"aids": asset_ids},
            )
            await session.commit()

    async def list_asset_chunks(
        self,
        asset_id: str,
        user_id: str,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """List an asset's chunks for preview — owner-scoped, capped by limit."""
        await self._ensure_table()
        from core.infra.database import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            rows = await session.execute(
                text(
                    """
                    SELECT id, text, tags, metadata, enabled
                    FROM vector_chunks
                    WHERE asset_id = :aid AND user_id = :uid
                    ORDER BY id
                    LIMIT :lim
                    """
                ),
                {"aid": asset_id, "uid": user_id, "lim": limit},
            )
            return [
                {
                    "id": r[0],
                    "text": r[1],
                    "tags": r[2] if r[2] else [],
                    "metadata": r[3] if r[3] else {},
                    "enabled": bool(r[4]) if r[4] is not None else True,
                }
                for r in rows.fetchall()
            ]

    async def clear_session(self, session_id: str) -> None:
        await self._ensure_table()
        from core.infra.database import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            await session.execute(
                text("DELETE FROM vector_chunks WHERE session_id = :sid"),
                {"sid": session_id},
            )
            await session.commit()


def _scope_filters(
    params: dict[str, Any],
    session_id: str | None,
    tag_filter: list[str] | None,
    asset_ids: list[str] | None,
) -> list[str]:
    """Shared WHERE fragments for scoped chunk queries; binds SQL params.

    ``asset_ids`` uses tri-state semantics: None = unfiltered, [] = match
    nothing, non-empty = restricted set. Caller appends ``user_id = :uid``.
    """
    clauses: list[str] = []
    if session_id:
        clauses.append("session_id = :sid")
        params["sid"] = session_id

    if tag_filter:
        tag_conditions = []
        for i, tag in enumerate(tag_filter):
            param_name = f"tag{i}"
            tag_conditions.append(f":{param_name} = ANY(tags)")
            params[param_name] = tag.lower()
        clauses.append("(" + " OR ".join(tag_conditions) + ")")

    if asset_ids is not None:
        if not asset_ids:
            clauses.append("FALSE")
        else:
            clauses.append("asset_id = ANY(:aids)")
            params["aids"] = asset_ids
    return clauses


def _rows_to_dicts(rows: Sequence[Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": row[0],
            "text": row[1],
            "tags": row[2] if row[2] else [],
            "session_id": row[3],
            "run_id": row[4],
            "asset_id": row[5],
            "metadata": row[6] if row[6] else {},
            "similarity": round(float(row[7]), 4),
        }
        for row in rows
    ]


def _rrf_fuse(
    legs: list[list[dict[str, Any]]], top_k: int, k: int = _RRF_K
) -> list[dict[str, Any]]:
    """Fuse ranked legs with Reciprocal Rank Fusion: sum of 1/(k + rank)."""
    merged: dict[str, dict[str, Any]] = {}
    for leg in legs:
        for rank, row in enumerate(leg, start=1):
            entry = merged.setdefault(row["id"], {**row, "score": 0.0})
            entry["score"] += 1.0 / (k + rank)
    return sorted(merged.values(), key=lambda r: r["score"], reverse=True)[:top_k]
