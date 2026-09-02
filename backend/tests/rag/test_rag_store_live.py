"""Live-database RAG integration tests — real pgvector + pg_trgm.

Unlike the mocked unit tests, these run the actual SQL against the real
postgres container (ragbase-db, 5433, pgvector/pg16) to prove the retrieval
pipeline works end-to-end on the production engine: hybrid legs, RRF fusion,
min_score filtering, user isolation, and cleanup.

Run: pytest tests/rag/test_rag_store_live.py -m integration
Requires: ragbase-db container up (docker compose up -d postgres) and the
backend reachable (conftest integration gate).
"""

import json
import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

pytestmark = pytest.mark.integration

_TEST_USER = "live-test-" + uuid.uuid4().hex[:12]

DB_URL = os.environ.get(
    "LIVE_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5433/ragbase",
)


@pytest.fixture
async def engine():
    eng = create_async_engine(DB_URL, pool_pre_ping=True)
    yield eng
    await eng.dispose()


@pytest.fixture
async def clean_test_rows(engine):
    """Remove any rows this test user left behind (previous runs/aborts)."""
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM vector_chunks WHERE user_id LIKE 'live-test-%'")
        )
        await conn.execute(
            text("DELETE FROM vector_chunks WHERE user_id LIKE 'live-other-%'")
        )
    yield
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM vector_chunks WHERE user_id LIKE 'live-test-%'")
        )
        await conn.execute(
            text("DELETE FROM vector_chunks WHERE user_id LIKE 'live-other-%'")
        )


def _emb(value: float, dim: int = 1024) -> str:
    return "[" + ",".join(str(value) for _ in range(dim)) + "]"


async def _insert_row(engine, chunk_id: str, emb: str, user_id: str, asset_id: str | None = None, meta: dict | None = None) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO vector_chunks
                    (id, session_id, run_id, text, tags, embedding, user_id, asset_id, metadata)
                VALUES (:id, :sid, :rid, :text, :tags, CAST(:emb AS vector),
                        :uid, :aid, CAST(:meta AS jsonb))
                """
            ),
            {
                "id": chunk_id,
                "sid": "live-sess",
                "rid": "live-run",
                "text": f"chunk {chunk_id} about postgres vector search",
                "tags": ["live"],
                "emb": emb,
                "uid": user_id,
                "aid": asset_id,
                "meta": json.dumps(meta or {"asset_name": "live-doc"}),
            },
        )


class TestLiveVectorStore:
    async def test_hybrid_search_returns_ranked_rows(self, engine, clean_test_rows):
        # Two chunks with distinct embeddings; query vector closer to chunk A.
        await _insert_row(engine, "live-a", _emb(1.0), _TEST_USER, "asset-1")
        await _insert_row(engine, "live-b", _emb(-1.0), _TEST_USER, "asset-2")

        async with engine.connect() as conn:
            vec_rows = (
                await conn.execute(
                    text(
                        """
                        SELECT id, 1 - (embedding <=> CAST(:emb AS vector)) AS sim
                        FROM vector_chunks
                        WHERE user_id = :uid
                        ORDER BY embedding <=> CAST(:emb AS vector)
                        LIMIT 5
                        """
                    ),
                    {"emb": _emb(0.95), "uid": _TEST_USER},
                )
            ).all()
            assert len(vec_rows) == 2
            ids = [r[0] for r in vec_rows]
            sims = [round(r[1], 3) for r in vec_rows]
            assert ids == ["live-a", "live-b"]
            assert sims[0] > sims[1]

    async def test_min_score_filters_low_similarity(self, engine, clean_test_rows):
        await _insert_row(engine, "live-a", _emb(1.0), _TEST_USER)
        await _insert_row(engine, "live-b", _emb(-1.0), _TEST_USER)

        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        """
                        SELECT id, 1 - (embedding <=> CAST(:emb AS vector)) AS sim
                        FROM vector_chunks
                        WHERE user_id = :uid
                          AND (1 - (embedding <=> CAST(:emb AS vector))) >= :min_score
                        ORDER BY embedding <=> CAST(:emb AS vector)
                        """
                    ),
                    {"emb": _emb(0.95), "uid": _TEST_USER, "min_score": 0.5},
                )
            ).all()
            ids = [r[0] for r in rows]
            assert ids == ["live-a"]  # live-b (cos ≈ -1) dropped below floor

    async def test_user_isolation(self, engine, clean_test_rows):
        other = "live-other-" + uuid.uuid4().hex[:8]
        await _insert_row(engine, "live-mine", _emb(1.0), _TEST_USER)
        await _insert_row(engine, "live-theirs", _emb(1.0), other)

        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        """
                        SELECT id FROM vector_chunks
                        WHERE user_id = :uid
                        ORDER BY embedding <=> CAST(:emb AS vector)
                        """
                    ),
                    {"emb": _emb(1.0), "uid": _TEST_USER},
                )
            ).all()
            ids = [r[0] for r in rows]
            assert "live-theirs" not in ids
            assert "live-mine" in ids

    async def test_lexical_leg_pg_trgm_matches_keyword(self, engine, clean_test_rows):
        # word_similarity needs ≥3 chars; "vector" is a trigram-carrier token.
        await _insert_row(engine, "live-lex", _emb(0.0), _TEST_USER)

        async with engine.connect() as conn:
            await conn.execute(text("SET LOCAL pg_trgm.word_similarity_threshold = 0.3"))
            rows = (
                await conn.execute(
                    text(
                        """
                        SELECT id, word_similarity(:q, text) AS sim
                        FROM vector_chunks
                        WHERE user_id = :uid AND text <% :q
                        ORDER BY word_similarity(:q, text) DESC
                        """
                    ),
                    {"q": "vector search", "uid": _TEST_USER},
                )
            ).all()
            ids = [r[0] for r in rows]
            assert "live-lex" in ids

    async def test_clear_asset_removes_only_that_asset(self, engine, clean_test_rows):
        await _insert_row(engine, "live-a1", _emb(1.0), _TEST_USER, "asset-clear")
        await _insert_row(engine, "live-a2", _emb(1.0), _TEST_USER, "asset-keep")

        async with engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM vector_chunks WHERE asset_id = :aid"), {"aid": "asset-clear"}
            )
        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    text("SELECT id FROM vector_chunks WHERE user_id = :uid"),
                    {"uid": _TEST_USER},
                )
            ).all()
            ids = [r[0] for r in rows]
            assert "live-a1" not in ids
            assert "live-a2" in ids

    async def test_cross_user_lexical_leg_isolated(self, engine, clean_test_rows):
        """OWASP LLM08 #2: user B's keyword query must not match A's chunks."""
        other = "live-other-" + uuid.uuid4().hex[:8]
        await _insert_row(engine, "live-secret", _emb(0.0), _TEST_USER, "asset-secret")

        async with engine.connect() as conn:
            await conn.execute(text("SET LOCAL pg_trgm.word_similarity_threshold = 0.3"))
            rows = (
                await conn.execute(
                    text(
                        """
                        SELECT id FROM vector_chunks
                        WHERE user_id = :uid AND text <% :q
                        """
                    ),
                    {"q": "postgres vector search", "uid": other},
                )
            ).all()
        assert rows == []

    async def test_cross_user_hybrid_attack_zero_hits(self, engine, clean_test_rows):
        """OWASP LLM08 #2: exact-match query by user B surfaces zero of A's chunks."""
        other = "live-other-" + uuid.uuid4().hex[:8]
        await _insert_row(engine, "live-secret", _emb(0.95), _TEST_USER, "asset-secret")

        async with engine.connect() as conn:
            vec_rows = (
                await conn.execute(
                    text(
                        """
                        SELECT id FROM vector_chunks
                        WHERE user_id = :uid
                        ORDER BY embedding <=> CAST(:emb AS vector)
                        """
                    ),
                    {"emb": _emb(0.95), "uid": other},
                )
            ).all()
            await conn.execute(text("SET LOCAL pg_trgm.word_similarity_threshold = 0.3"))
            lex_rows = (
                await conn.execute(
                    text(
                        """
                        SELECT id FROM vector_chunks
                        WHERE user_id = :uid AND text <% :q
                        """
                    ),
                    {"q": "chunk live-secret about postgres vector search", "uid": other},
                )
            ).all()
        assert vec_rows == []
        assert lex_rows == []

    async def test_store_hybrid_search_end_to_end(self, engine, clean_test_rows):
        """走 PgVectorStore API 全链路：add（真实 upsert SQL）→ search（双 leg
        + RRF 融合 + 用户隔离），验证 store 本身而非手写 SQL。"""
        from unittest.mock import patch

        from rag.rag_chunking import Chunk
        from rag.rag_store import PgVectorStore

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        store = PgVectorStore()
        with patch(
            "core.infra.database.get_session_factory", return_value=session_factory
        ):
            await store.add(
                [
                    Chunk(
                        id="live-e2e-a",
                        text="postgres vector search hybrid retrieval",
                        session_id="live-sess",
                        run_id="live-run",
                        embedding=[1.0] * 1024,
                        metadata={"asset_id": "e2e-a"},
                    ),
                    Chunk(
                        id="live-e2e-b",
                        text="unrelated cooking recipes",
                        session_id="live-sess",
                        run_id="live-run",
                        embedding=[-1.0] * 1024,
                        metadata={"asset_id": "e2e-b"},
                    ),
                ],
                user_id=_TEST_USER,
            )
            results = await store.search(
                [0.9] * 1024,
                query_text="postgres vector search",
                user_id=_TEST_USER,
                top_k=5,
            )

        texts = [r["text"] for r in results]
        # A 双 leg 命中排第一；B 向量腿相似度为负但仍入列（无 min_score 地板）。
        assert "postgres vector search hybrid retrieval" in texts
        assert "unrelated cooking recipes" in texts
        assert results[0]["similarity"] > results[1]["similarity"]
        # 检索结果携带资产溯源，供引文 UI。
        assert results[0]["metadata"]["asset_id"] == "e2e-a"
