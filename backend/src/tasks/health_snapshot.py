"""Hourly health-score snapshot — Celery beat entry (error-budget model).

Samples every user with recent retrieval/feedback activity, computes the
24h composite score via ``services.health_score`` and persists one row per
user so the monitoring page renders a score trend that is independent of
dashboard polling. Old rows are pruned on each run. Per-user failures are
contained (fail-open) so one dirty dataset never blocks everyone else.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from core.infra.logging_config import get_logger

logger = get_logger(__name__)


async def _health_snapshot() -> dict[str, int]:
    from core.infra.database import FeedbackLog, RetrievalLogDB, get_session_factory
    from repository.health_history import (
        prune_health_snapshots,
        record_health_snapshot,
    )
    from repository.monitoring import feedback_summary, retrieval_summary
    from services.health_score import compute_health_score
    from sqlalchemy import distinct, select

    cutoff = datetime.now(UTC) - timedelta(hours=24)
    factory = get_session_factory()
    async with factory() as session:
        retrieval_users = (
            await session.execute(
                select(distinct(RetrievalLogDB.user_id)).where(
                    RetrievalLogDB.created_at >= cutoff
                )
            )
        ).scalars()
        feedback_users = (
            await session.execute(
                select(distinct(FeedbackLog.user_id)).where(
                    FeedbackLog.created_at >= cutoff
                )
            )
        ).scalars()
        users = sorted({*retrieval_users, *feedback_users})

    snapped = 0
    failed = 0
    for user_id in users:
        try:
            retrieval = await retrieval_summary(user_id, 24)
            feedback = await feedback_summary(user_id, 24)
            health = compute_health_score(retrieval, feedback)
            await record_health_snapshot(
                user_id, health["score"], health["factors"], window_hours=24
            )
            snapped += 1
        except Exception:
            # Fail-open: 一个用户的数据问题不能阻断其余用户的快照。
            failed += 1
            logger.warning("health snapshot failed for %s", user_id, exc_info=True)

    pruned = await prune_health_snapshots()
    return {
        "users": len(users),
        "snapshots": snapped,
        "failed": failed,
        "pruned": pruned,
    }


def run_health_snapshot() -> dict[str, Any]:
    """Sync entrypoint for the Celery task wrapper."""
    return asyncio.run(_health_snapshot())
