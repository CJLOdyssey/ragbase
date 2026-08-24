"""Persisted health-score snapshots (hourly Celery beat) + history reads.

Snapshots decouple the score trend from dashboard polling: the beat task
samples every active user's 24h error-budget score once an hour, and the
monitoring page reads back a bounded ascending series.
"""

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from core.infra.database import HealthScoreSnapshotDB, get_session_factory
from sqlalchemy import delete, select


async def record_health_snapshot(
    user_id: str,
    score: int | None,
    factors: Sequence[Mapping[str, Any]],
    window_hours: int = 24,
) -> str:
    """Insert one snapshot row; returns its id."""
    factory = get_session_factory()
    async with factory() as session:
        row = HealthScoreSnapshotDB(
            user_id=user_id,
            score=score,
            factors=json.dumps(factors, ensure_ascii=False),
            window_hours=window_hours,
        )
        session.add(row)
        await session.commit()
        return row.id


async def list_health_snapshots(user_id: str, hours: int = 168) -> list[dict[str, Any]]:
    """Ascending snapshot series for the last ``hours`` (0 = all)."""
    factory = get_session_factory()
    async with factory() as session:
        conds = [HealthScoreSnapshotDB.user_id == user_id]
        if hours > 0:
            conds.append(
                HealthScoreSnapshotDB.created_at
                >= datetime.now(UTC) - timedelta(hours=hours)
            )
        rows = (
            (
                await session.execute(
                    select(
                        HealthScoreSnapshotDB.created_at,
                        HealthScoreSnapshotDB.score,
                        HealthScoreSnapshotDB.factors,
                    )
                    .where(*conds)
                    .order_by(HealthScoreSnapshotDB.created_at.asc())
                )
            )
            .all()
        )
    return [
        {
            "ts": r.created_at.isoformat() if r.created_at else None,
            "score": r.score,
            "factors": json.loads(r.factors) if r.factors else None,
        }
        for r in rows
    ]


async def prune_health_snapshots(keep_days: int = 90) -> int:
    """Delete snapshots older than ``keep_days``; returns rows removed."""
    cutoff = datetime.now(UTC) - timedelta(days=keep_days)
    factory = get_session_factory()
    async with factory() as session:
        result: Any = await session.execute(
            delete(HealthScoreSnapshotDB).where(
                HealthScoreSnapshotDB.created_at < cutoff
            )
        )
        await session.commit()
        return int(getattr(result, "rowcount", 0) or 0)
