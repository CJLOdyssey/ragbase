"""Online quality metrics aggregation + alert evaluation (R3, ENTERPRISE_RAG_TOP_BAR §4 #7).

Read-only analytics over the append-only retrieval_logs and feedback_logs.
Counts are aggregated in SQL; latency percentiles are computed in Python
from the latest bounded sample of the window (see ``monitoring_shared``).
Time-bucketed grids live in the sibling ``monitoring_timeseries`` module.
"""

from datetime import datetime
from typing import Any

from core.infra.database import (
    FeedbackLog,
    FeedbackReviewDB,
    ProjectRun,
    RetrievalLogDB,
    SessionDB,
    get_session_factory,
)
from core.infra.logging_config import get_logger
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.sql.functions import FunctionElement

from repository.monitoring_shared import (
    LATENCY_SAMPLE_LIMIT,
    ROOT_CAUSES,
    percentile_nearest_rank,
    resolve_window_lower,
    window_conds,
)

logger = get_logger(__name__)


async def retrieval_summary(
    user_id: str,
    window_hours: int,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    latency_slo_ms: int = 8000,
) -> dict[str, Any]:
    """Aggregate retrieval activity in the window: volume, empty recall, latency.

    ``window_hours <= 0`` means "all time"; explicit ``since``/``until``
    override the sliding-window bounds. ``latency_slo_ms`` defines the
    slow-request boundary feeding the error-budget health score (the share
    of requests above it is mathematically equivalent to the p95 SLO).
    """
    lower = resolve_window_lower(window_hours, since)
    factory = get_session_factory()
    async with factory() as session:
        agg = (
            select(
                func.count().label("total"),
                func.count().filter(RetrievalLogDB.hit_count <= 0).label("empty"),
                func.count()
                .filter(RetrievalLogDB.latency_ms > latency_slo_ms)
                .label("slow"),
                func.avg(RetrievalLogDB.hit_count).label("avg_hits"),
            ).where(
                *window_conds(
                    RetrievalLogDB.user_id,
                    RetrievalLogDB.created_at,
                    user_id,
                    lower,
                    until,
                )
            )
        )
        row = (await session.execute(agg)).one()
        total = int(row.total)
        empty_recall = int(row.empty)
        slow_count = int(row.slow)
        avg_hits = round(float(row.avg_hits), 2) if row.avg_hits is not None else None
        latency_stmt = (
            select(RetrievalLogDB.latency_ms)
            .where(
                *window_conds(
                    RetrievalLogDB.user_id,
                    RetrievalLogDB.created_at,
                    user_id,
                    lower,
                    until,
                )
            )
            # Newest-first sample: with more rows than the cap, the most
            # recent traffic (not the window's tail) drives alerting.
            .order_by(RetrievalLogDB.created_at.desc())
            .limit(LATENCY_SAMPLE_LIMIT)
        )
        latencies = list((await session.execute(latency_stmt)).scalars())
    return {
        "total": total,
        "empty_recall_count": empty_recall,
        "empty_recall_rate": (empty_recall / total) if total else 0.0,
        "slow_count": slow_count,
        # Error-budget view: the share of requests above the SLO boundary,
        # the event-level equivalent of the p95 threshold.
        "slow_rate": (slow_count / total) if total else 0.0,
        "avg_hit_count": avg_hits,
        "latency_p50_ms": percentile_nearest_rank(latencies, 50),
        "latency_p95_ms": percentile_nearest_rank(latencies, 95),
        "latency_p99_ms": percentile_nearest_rank(latencies, 99),
    }


async def feedback_summary(
    user_id: str,
    window_hours: int,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Aggregate answer-quality feedback in the window: volume and good ratio.

    ``window_hours <= 0`` means "all time".
    """
    lower = resolve_window_lower(window_hours, since)
    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(
                func.count().label("total"),
                func.count().filter(FeedbackLog.rating == "good").label("good"),
            ).where(
                *window_conds(
                    FeedbackLog.user_id,
                    FeedbackLog.created_at,
                    user_id,
                    lower,
                    until,
                )
            )
        )
        row = (await session.execute(stmt)).one()
        total = int(row.total)
        good = int(row.good)

        # Coverage denominator: successfully answered runs in the window —
        # the good ratio is only trustworthy when backed by enough answers.
        answered = 0
        try:
            conds = [ProjectRun.status == "converged"]
            if lower is not None:
                conds.append(ProjectRun.created_at >= lower)
            if until is not None:
                conds.append(ProjectRun.created_at <= until)
            answered_stmt = (
                select(func.count())
                .select_from(ProjectRun)
                .join(SessionDB, ProjectRun.session_id == SessionDB.id)
                .where(SessionDB.user_id == user_id, *conds)
            )
            answered = int((await session.execute(answered_stmt)).scalar() or 0)
        except Exception:
            # A missing denominator degrades the summary, never blocks it.
            logger.warning(
                "answered-runs count failed for user %s", user_id, exc_info=True
            )
            answered = 0

    return {
        "total": total,
        "good_count": good,
        "bad_count": total - good,
        "good_ratio": (good / total) if total else None,
        "answered_runs": answered,
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


async def root_cause_breakdown(
    user_id: str,
    window_hours: int,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Aggregate bad-feedback triage state in the window.

    Single-pass conditional aggregation over bad ratings joined to their
    review records: status mix (unreviewed ≡ pending) + per-root-cause
    counts. ``window_hours <= 0`` means "all time".
    """
    lower = resolve_window_lower(window_hours, since)
    factory = get_session_factory()
    async with factory() as session:
        conds = window_conds(
            FeedbackLog.user_id,
            FeedbackLog.created_at,
            user_id,
            lower,
            until,
        )
        conds.append(FeedbackLog.rating == "bad")

        cols: list[ColumnElement[Any]] = [func.count().label("total")]
        for cause in ROOT_CAUSES:
            cols.append(
                func.count()
                .filter(FeedbackReviewDB.root_cause == cause)
                .label(f"c_{cause}")
            )
        cols.append(
            func.count()
            .filter(FeedbackReviewDB.status == "resolved")
            .label("resolved")
        )
        cols.append(
            func.count()
            .filter(FeedbackReviewDB.status == "dismissed")
            .label("dismissed")
        )
        stmt = (
            select(*cols)
            .select_from(FeedbackLog)
            .outerjoin(FeedbackReviewDB, FeedbackReviewDB.feedback_id == FeedbackLog.id)
            .where(*conds)
        )
        row = (await session.execute(stmt)).one()

    total = int(row.total)
    resolved = int(row.resolved)
    dismissed = int(row.dismissed)
    return {
        "window_hours": window_hours,
        "total_bad": total,
        # Unreviewed bad feedback counts as pending (a NULL review row hits
        # neither status filter).
        "pending": total - resolved - dismissed,
        "resolved": resolved,
        "dismissed": dismissed,
        "causes": [
            {"cause": cause, "count": int(getattr(row, f"c_{cause}"))}
            for cause in ROOT_CAUSES
        ],
    }


async def top_queries(
    user_id: str,
    window_hours: int,
    *,
    kind: str = "empty",
    limit: int = 10,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Rank recurring problem queries in the window.

    ``kind="empty"`` ranks zero-hit queries by frequency (corpus gaps to
    fill); ``kind="slow"`` ranks by average latency (performance hotspots).
    ``window_hours <= 0`` means "all time".
    """
    lower = resolve_window_lower(window_hours, since)
    factory = get_session_factory()
    async with factory() as session:
        conds = window_conds(
            RetrievalLogDB.user_id,
            RetrievalLogDB.created_at,
            user_id,
            lower,
            until,
        )
        order_col: FunctionElement[Any]
        if kind == "empty":
            conds.append(RetrievalLogDB.hit_count <= 0)
            order_col = func.count()
        else:
            order_col = func.avg(RetrievalLogDB.latency_ms)

        stmt = (
            select(
                RetrievalLogDB.query.label("query"),
                func.count().label("n"),
                func.avg(RetrievalLogDB.latency_ms).label("avg_latency"),
            )
            .where(*conds)
            .group_by(RetrievalLogDB.query)
            .order_by(order_col.desc())
            .limit(limit)
        )
        rows = (await session.execute(stmt)).all()

    return {
        "window_hours": window_hours,
        "kind": kind,
        "items": [
            {
                "query": r.query,
                "count": int(r.n),
                "avg_latency_ms": (
                    round(float(r.avg_latency)) if r.avg_latency is not None else None
                ),
            }
            for r in rows
        ],
    }
