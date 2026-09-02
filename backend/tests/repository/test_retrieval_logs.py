"""Retrieval activity log repository tests (unit, in-memory sqlite)."""

from core.infra.database import RetrievalLogDB, get_session_factory
from repository.retrieval_logs import create_retrieval_log
from sqlalchemy import select


class TestCreateRetrievalLog:
    async def test_writes_row_with_sources(self):
        await create_retrieval_log(
            user_id="u1",
            session_id="s1",
            query="什么是产品发布？",
            latency_ms=42,
            hit_count=2,
            sources=[{"asset_id": "a1", "asset_name": "手册", "similarity": 0.9, "text": "发布流程分三步"}],
        )

        factory = get_session_factory()
        async with factory() as session:
            rows = (await session.execute(select(RetrievalLogDB))).scalars().all()

        assert len(rows) == 1
        row = rows[0]
        assert row.user_id == "u1"
        assert row.session_id == "s1"
        assert row.query == "什么是产品发布？"
        assert row.latency_ms == 42
        assert row.hit_count == 2
        assert row.top_k == 5
        assert row.rerank is False
        assert row.min_score is None
        assert '"asset_name": "手册"' in (row.sources or "")
        assert '"text": "发布流程分三步"' in (row.sources or "")

    async def test_writes_row_without_sources(self):
        await create_retrieval_log(user_id="u1", query="q", latency_ms=1, hit_count=0)

        factory = get_session_factory()
        async with factory() as session:
            rows = (await session.execute(select(RetrievalLogDB))).scalars().all()

        assert len(rows) == 1
        assert rows[0].sources is None

    async def test_custom_top_k_rerank_min_score(self):
        await create_retrieval_log(
            user_id="u1",
            query="q",
            latency_ms=5,
            hit_count=1,
            top_k=3,
            rerank=True,
            min_score=0.45,
        )

        factory = get_session_factory()
        async with factory() as session:
            row = (
                await session.execute(select(RetrievalLogDB))
            ).scalars().one()

        assert row.top_k == 3
        assert row.rerank is True
        assert row.min_score == 0.45
