"""Shadow retrieval log (O4) repository tests — create + serialization."""


import pytest
from orm import ShadowRetrievalLogDB
from repository.shadow_retrieval import _sources_json, create_shadow_log
from sqlalchemy import func, select


@pytest.mark.asyncio
async def test_create_shadow_log_persists_all_fields(db_engine):
    sources = [
        {"asset_id": "a-1", "asset_name": "spec.md", "similarity": 0.92, "extra": "ignored"},
        {"asset_id": "a-2", "asset_name": "runbook.md", "similarity": 0.81},
    ]
    await create_shadow_log(
        user_id="u-1",
        session_id="s-1",
        query="如何部署",
        variant="rerank",
        latency_ms=120,
        hit_count=3,
        top_k=8,
        rerank=True,
        min_score=0.4,
        sources=sources,
    )

    from core.infra.database import get_session_factory

    async with get_session_factory()() as session:
        rows = (await session.execute(select(ShadowRetrievalLogDB))).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.user_id == "u-1"
    assert row.session_id == "s-1"
    assert row.query == "如何部署"
    assert row.variant == "rerank"
    assert row.latency_ms == 120
    assert row.hit_count == 3
    assert row.top_k == 8
    assert row.rerank is True
    assert row.min_score == 0.4
    assert row.sources is not None and "spec.md" in row.sources and "runbook.md" in row.sources
    assert "extra" not in (row.sources or "")


@pytest.mark.asyncio
async def test_create_shadow_log_minimal_defaults(db_engine):
    await create_shadow_log(user_id="u-2", query="q", variant="base", latency_ms=5, hit_count=0)

    from core.infra.database import get_session_factory

    async with get_session_factory()() as session:
        count = (await session.execute(select(func.count()).select_from(ShadowRetrievalLogDB))).scalar_one()
    assert count == 1


def test_sources_json_none_and_empty():
    assert _sources_json(None) is None
    assert _sources_json([]) is None


def test_sources_json_serializes_fields():
    raw = _sources_json([{"asset_id": "a", "asset_name": "名.md", "similarity": 0.5}])
    assert raw is not None
    assert '"asset_id": "a"' in raw
    assert '"asset_name": "名.md"' in raw
    assert '"similarity": 0.5' in raw


@pytest.mark.asyncio
async def test_shadow_logs_are_append_only(db_engine):
    for _ in range(3):
        await create_shadow_log(user_id="u-3", query="q", variant="v", latency_ms=1, hit_count=0)

    from core.infra.database import get_session_factory

    async with get_session_factory()() as session:
        count = (await session.execute(select(func.count()).select_from(ShadowRetrievalLogDB))).scalar_one()
    assert count == 3
