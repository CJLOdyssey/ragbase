"""Health snapshot beat task — integration through the real repository layer.

Lives under tests/repository so the shared in-memory sqlite fixtures
(autouse _setup_db) provide the schema; the task itself is a thin
orchestration of repository + service functions.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

pytestmark = pytest.mark.unit

from core.infra.database import (
    FeedbackLog,
    HealthScoreSnapshotDB,
    RetrievalLogDB,
    get_session_factory,
)
from sqlalchemy import select
from tasks.health_snapshot import _health_snapshot


async def _seed_activity(user_id: str) -> None:
    factory = get_session_factory()
    async with factory() as session:
        session.add(
            RetrievalLogDB(
                user_id=user_id,
                query="q",
                latency_ms=100,
                hit_count=3,
                created_at=datetime.now(UTC),
            )
        )
        session.add(
            FeedbackLog(
                run_id="r1",
                user_id=user_id,
                rating="good",
                created_at=datetime.now(UTC),
            )
        )
        await session.commit()


async def _inject_stale_snapshot(user_id: str, days_old: int) -> None:
    factory = get_session_factory()
    async with factory() as session:
        session.add(
            HealthScoreSnapshotDB(
                user_id=user_id,
                score=50,
                created_at=datetime.now(UTC) - timedelta(days=days_old),
            )
        )
        await session.commit()


async def _read_snapshots() -> list[HealthScoreSnapshotDB]:
    factory = get_session_factory()
    async with factory() as session:
        rows = (
            (
                await session.execute(
                    select(HealthScoreSnapshotDB).order_by(
                        HealthScoreSnapshotDB.created_at.asc()
                    )
                )
            )
            .scalars()
            .all()
        )
    return list(rows)


class TestHealthSnapshotTask:
    async def test_snapshots_recent_active_users_with_budget_score(self):
        await _seed_activity("u1")
        result = await _health_snapshot()
        assert result["users"] == 1
        assert result["snapshots"] == 1

        rows = await _read_snapshots()
        assert len(rows) == 1
        # 错误预算模型：单条好样本 → 检索/延迟预算满格 100，反馈样本不足 → null。
        assert rows[0].score == 100
        assert rows[0].window_hours == 24
        assert '"satisfaction"' in (rows[0].factors or "")
        assert '"score": null' in (rows[0].factors or "")

    async def test_old_rows_pruned_each_run(self):
        await _seed_activity("u1")
        await _inject_stale_snapshot("u1", days_old=120)
        result = await _health_snapshot()
        assert result["pruned"] == 1
        remaining = await _read_snapshots()
        # 过期快照（score=50）被清掉，只剩本次新采样。
        assert [r.score for r in remaining] == [100]

    async def test_fail_open_per_user(self, monkeypatch):
        """单个用户数据异常只跳过该用户，不阻断其余快照。"""
        from repository import monitoring as monitoring_repo

        await _seed_activity("u1")
        await _seed_activity("u2")
        original = monitoring_repo.retrieval_summary

        async def flaky(user_id: str, *args: Any, **kwargs: Any):
            if user_id == "u1":
                raise RuntimeError("dirty data")
            return await original(user_id, *args, **kwargs)

        monkeypatch.setattr(monitoring_repo, "retrieval_summary", flaky)
        result = await _health_snapshot()
        assert result["users"] == 2
        assert result["snapshots"] == 1
        assert result["failed"] == 1
        rows = await _read_snapshots()
        assert len(rows) == 1
