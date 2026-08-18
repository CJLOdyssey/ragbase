"""Online quality metrics aggregation + alert evaluation (R3, ENTERPRISE_RAG_TOP_BAR §4 #7).

Read-only analytics over the append-only retrieval_logs and feedback_logs.
Counts are aggregated in SQL; latency percentiles are computed in Python
from the latest bounded sample of the window. PostgreSQL has native
percentile_cont(), but the in-memory sqlite used by unit tests does not —
the nearest-rank Python percentile keeps behavior identical across both.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from core.infra.database import FeedbackLog, RetrievalLogDB, get_session_factory
from sqlalchemy import func, select

# Cap latency samples pulled for percentile computation (defensive bound for
# very large windows — alerting percentiles stay stable beyond this).
_LATENCY_SAMPLE_LIMIT = 10000


async def retrieval_summary(user_id: str, window_hours: int) -> dict[str, Any]:
    """Aggregate retrieval activity in the window: volume, empty recall, latency."""
    since = datetime.now(UTC) - timedelta(hours=window_hours)
    factory = get_session_factory()
    async with factory() as session:
        agg = (
            select(
                func.count().label("total"),
                func.count().filter(RetrievalLogDB.hit_count <= 0).label("empty"),
            ).where(
                RetrievalLogDB.user_id == user_id,
                RetrievalLogDB.created_at >= since,
            )
        )
        row = (await session.execute(agg)).one()
        total = int(row.total)
        empty_recall = int(row.empty)
        latency_stmt = (
            select(RetrievalLogDB.latency_ms)
            .where(
                RetrievalLogDB.user_id == user_id,
                RetrievalLogDB.created_at >= since,
            )
            # Newest-first sample: with more rows than the cap, the most
            # recent traffic (not the window's tail) drives alerting.
            .order_by(RetrievalLogDB.created_at.desc())
            .limit(_LATENCY_SAMPLE_LIMIT)
        )
        latencies = list((await session.execute(latency_stmt)).scalars())
    return {
        "total": total,
        "empty_recall_count": empty_recall,
        "empty_recall_rate": (empty_recall / total) if total else 0.0,
        "latency_p50_ms": _percentile(latencies, 50),
        "latency_p95_ms": _percentile(latencies, 95),
    }


async def feedback_summary(user_id: str, window_hours: int) -> dict[str, Any]:
    """Aggregate answer-quality feedback in the window: volume and good ratio."""
    since = datetime.now(UTC) - timedelta(hours=window_hours)
    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(
                func.count().label("total"),
                func.count().filter(FeedbackLog.rating == "good").label("good"),
            ).where(
                FeedbackLog.user_id == user_id,
                FeedbackLog.created_at >= since,
            )
        )
        row = (await session.execute(stmt)).one()
    total = int(row.total)
    good = int(row.good)
    return {
        "total": total,
        "good_count": good,
        "bad_count": total - good,
        "good_ratio": (good / total) if total else None,
    }


def evaluate_alerts(
    retrieval: dict[str, Any],
    feedback: dict[str, Any],
    *,
    max_empty_recall_pct: float = 15.0,
    max_p95_latency_ms: int = 8000,
    min_good_ratio: float = 0.6,
) -> list[dict[str, Any]]:
    """Compare metrics against thresholds; pure, fully unit-testable."""
    alerts: list[dict[str, Any]] = []

    empty_pct = retrieval.get("empty_recall_rate", 0.0) * 100
    if retrieval.get("total", 0) > 0 and empty_pct > max_empty_recall_pct:
        alerts.append(_alert("warning", "empty_recall_high", empty_pct, max_empty_recall_pct))

    p95 = retrieval.get("latency_p95_ms")
    if p95 is not None and p95 > max_p95_latency_ms:
        alerts.append(_alert("warning", "p95_latency_high", p95, max_p95_latency_ms))

    good_ratio = feedback.get("good_ratio")
    if feedback.get("total", 0) > 0 and good_ratio is not None and good_ratio < min_good_ratio:
        alerts.append(_alert("warning", "good_ratio_low", good_ratio, min_good_ratio))

    return alerts


def _alert(level: str, code: str, current: float, threshold: float) -> dict[str, Any]:
    return {"level": level, "code": code, "current": current, "threshold": threshold}


def _percentile(values: list[int], pct: int) -> int | None:
    """Nearest-rank percentile; None when no samples."""
    if not values:
        return None
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round(pct / 100 * len(ordered)) - 1))
    return ordered[idx]
