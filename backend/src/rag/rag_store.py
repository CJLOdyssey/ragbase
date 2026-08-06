from typing import Any

"""pgvector vector store for RAG pipeline."""

from core.infra.logging_config import get_logger
from sqlalchemy import text

from rag.rag_chunking import Chunk
from rag.rag_embedding import EMBEDDING_DIM

logger = get_logger(__name__)


class PgVectorStore:
    """PostgreSQL + pgvector vector store.

    Requires:
      CREATE EXTENSION IF NOT EXISTS vector;
      Table: vector_chunks (id, session_id, run_id, text, tags, embedding vector(1024))
      Index: CREATE INDEX ON vector_chunks USING hnsw (embedding vector_cosine_ops);
    """

    def __init__(self) -> None:
        self._initialized = False

    async def _ensure_table(self) -> None:
        if self._initialized:
            return
        from core.infra.database import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            # Enable extension (requires superuser in production — run once manually)
            try:
                await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            except Exception:
                logger.warning("pgvector extension not available — install it first")

            # Create table if not exists
            await session.execute(
                text(f"""
                CREATE TABLE IF NOT EXISTS vector_chunks (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    run_id TEXT,
                    text TEXT NOT NULL,
                    tags TEXT[] DEFAULT '{{}}',
                    embedding vector({EMBEDDING_DIM})
                )
            """)
            )

            # Create index if not exists
            try:
                await session.execute(
                    text("""
                    CREATE INDEX IF NOT EXISTS idx_vector_chunks_embedding
                    ON vector_chunks USING hnsw (embedding vector_cosine_ops)
                """)
                )
            except Exception:
                # HNSW might not be available — try IVFFlat
                try:
                    await session.execute(
                        text("""
                        CREATE INDEX IF NOT EXISTS idx_vector_chunks_embedding
                        ON vector_chunks USING ivfflat (embedding vector_cosine_ops)
                    """)
                    )
                except Exception:
                    logger.warning("No vector index available — searches will be sequential")

            await session.commit()
        self._initialized = True

    async def add(self, chunks: list[Chunk]) -> None:
        """Insert chunks with embeddings into pgvector."""
        if not chunks:
            return
        await self._ensure_table()

        from core.infra.database import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            for chunk in chunks:
                if not chunk.embedding:
                    continue
                # Build vector literal safely from numeric values
                emb_str = "[" + ",".join(str(v) for v in chunk.embedding) + "]"
                # Use proper PostgreSQL array literal via CAST
                tags_array = "{" + ",".join(chunk.tags) + "}" if chunk.tags else "{}"
                await session.execute(
                    text(
                        """
                        INSERT INTO vector_chunks (id, session_id, run_id, text, tags, embedding)
                        VALUES (:id, :sid, :rid, :text, CAST(:tags AS text[]), CAST(:emb AS vector))
                        ON CONFLICT (id) DO UPDATE
                        SET text = EXCLUDED.text,
                            tags = EXCLUDED.tags,
                            embedding = EXCLUDED.embedding
                        """
                    ),
                    {
                        "id": chunk.id,
                        "sid": chunk.session_id,
                        "rid": chunk.run_id or "",
                        "text": chunk.text,
                        "tags": tags_array,
                        "emb": emb_str,
                    },
                )
            await session.commit()
        logger.info("pgvector: stored %d chunks", len(chunks))

    async def search(
        self,
        query_embedding: list[float],
        session_id: str | None = None,
        tag_filter: list[str] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Search with hybrid vector similarity and optional tag filter.

        Returns list of {text, score, tags, session_id, run_id}.
        """
        await self._ensure_table()

        from core.infra.database import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            emb_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

            where_clauses = []
            params = {"emb": emb_str, "top_k": top_k}

            if session_id:
                where_clauses.append("session_id = :sid")
                params["sid"] = session_id

            if tag_filter:
                tag_conditions = []
                for i, tag in enumerate(tag_filter):
                    param_name = f"tag{i}"
                    tag_conditions.append(f":{param_name} = ANY(tags)")
                    params[param_name] = tag.lower()
                where_clauses.append("(" + " OR ".join(tag_conditions) + ")")

            where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"

            result = await session.execute(
                text(f"""
                SELECT text, tags, session_id, run_id,
                       1 - (embedding <=> CAST(:emb AS vector)) AS similarity
                FROM vector_chunks
                WHERE {where_sql}
                ORDER BY embedding <=> CAST(:emb AS vector)
                LIMIT :top_k
            """),
                params,
            )

            rows = result.fetchall()
            return [
                {
                    "text": row[0],
                    "tags": row[1] if row[1] else [],
                    "session_id": row[2],
                    "run_id": row[3],
                    "score": round(float(row[4]), 4),
                }
                for row in rows
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
