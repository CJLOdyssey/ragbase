"""Online quality monitoring routes — R3 metrics + alerts (ENTERPRISE_RAG_TOP_BAR §4 #7).

Exposes per-user retrieval/feedback aggregates over a sliding window or an
explicit since/until range plus threshold-based alerts. Purely read-only;
metrics feed the frontend panel.
"""

from typing import Any

from auth import get_user_id
from fastapi import APIRouter, Depends, Query, Request

from routers.window_range import WindowBounds, bounded_window
from repository.monitoring import (
    evaluate_alerts,
    feedback_summary,
    quality_timeseries,
    retrieval_summary,
    root_cause_breakdown,
    top_queries,
)

router = APIRouter(tags=["monitoring"])


@router.get("/api/monitoring/summary")
async def get_quality_summary(
    request: Request,
    # window_hours=0 → all time (bounded grids in the timeseries endpoint).
    # since/until override the sliding window (validated in the dependency).
    bounds: WindowBounds = Depends(bounded_window),
    max_empty_recall_pct: float = Query(15.0, ge=0, le=100),
    max_p95_latency_ms: int = Query(8000, ge=1),
    min_good_ratio: float = Query(0.6, ge=0, le=1),
) -> Any:
    """Aggregate retrieval/feedback quality metrics with alerts for the window."""
    user_id = get_user_id(request)
    retrieval = await retrieval_summary(
        user_id, bounds.window_hours, since=bounds.since, until=bounds.until
    )
    feedback = await feedback_summary(
        user_id, bounds.window_hours, since=bounds.since, until=bounds.until
    )
    alerts = evaluate_alerts(
        retrieval,
        feedback,
        max_empty_recall_pct=max_empty_recall_pct,
        max_p95_latency_ms=max_p95_latency_ms,
        min_good_ratio=min_good_ratio,
    )
    return {
        "window_hours": bounds.window_hours,
        "retrieval": retrieval,
        "feedback": feedback,
        "alerts": alerts,
    }


@router.get("/api/monitoring/timeseries")
async def get_quality_timeseries(
    request: Request,
    bounds: WindowBounds = Depends(bounded_window),
    # 上期序列（ghost 线 + 真·环比基线），仅预设窗口语义下有效。
    include_previous: bool = Query(False),
) -> Any:
    """Retrieval/feedback trends on one aligned bucket grid (0 = all time)."""
    user_id = get_user_id(request)
    return await quality_timeseries(
        user_id,
        bounds.window_hours,
        include_previous=include_previous,
        since=bounds.since,
        until=bounds.until,
    )


@router.get("/api/monitoring/root-causes")
async def get_root_causes(
    request: Request,
    bounds: WindowBounds = Depends(bounded_window),
) -> Any:
    """Bad-feedback triage mix + per-root-cause counts (Pareto source)."""
    user_id = get_user_id(request)
    return await root_cause_breakdown(
        user_id, bounds.window_hours, since=bounds.since, until=bounds.until
    )


@router.get("/api/monitoring/top-queries")
async def get_top_queries(
    request: Request,
    bounds: WindowBounds = Depends(bounded_window),
    kind: str = Query("empty", pattern="^(empty|slow)$"),
    limit: int = Query(10, ge=1, le=50),
) -> Any:
    """Rank recurring problem queries: zero-hit by frequency or slow by latency."""
    user_id = get_user_id(request)
    return await top_queries(
        user_id,
        bounds.window_hours,
        kind=kind,
        limit=limit,
        since=bounds.since,
        until=bounds.until,
    )
