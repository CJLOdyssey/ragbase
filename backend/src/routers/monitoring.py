"""Online quality monitoring routes — R3 metrics + alerts (ENTERPRISE_RAG_TOP_BAR §4 #7).

Exposes per-user retrieval/feedback aggregates over a sliding window or an
explicit since/until range, the error-budget composite health score,
threshold alerts plus multi-window burn-rate alerts. Purely read-only;
metrics feed the frontend panel. Business orchestration lives in
``services.health_score`` — routers only bind HTTP to domain calls.
"""

from typing import Any

from auth import get_user_id
from fastapi import APIRouter, Depends, Query, Request
from repository.health_history import list_health_snapshots
from repository.latency_distribution import latency_heatmap, latency_scatter
from repository.monitoring import (
    root_cause_breakdown,
    top_queries,
)
from repository.monitoring_timeseries import quality_timeseries
from services.health_score import build_quality_summary

from routers.window_range import WindowBounds, bounded_window

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
    """Quality metrics + composite health score + threshold/burn-rate alerts."""
    return await build_quality_summary(
        get_user_id(request),
        bounds.window_hours,
        since=bounds.since,
        until=bounds.until,
        max_empty_recall_pct=max_empty_recall_pct,
        max_p95_latency_ms=max_p95_latency_ms,
        min_good_ratio=min_good_ratio,
    )


@router.get("/api/monitoring/health-score/history")
async def get_health_score_history(
    request: Request,
    hours: int = Query(168, ge=1, le=24 * 90),
) -> Any:
    """Ascending persisted score snapshots (hourly beat samples)."""
    user_id = get_user_id(request)
    points = await list_health_snapshots(user_id, hours)
    return {"hours": hours, "points": points}


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


@router.get("/api/monitoring/latency-heatmap")
async def get_latency_heatmap(
    request: Request,
    bounds: WindowBounds = Depends(bounded_window),
) -> Any:
    """Retrieval counts per time-bucket × fixed latency-bin (heatmap source)."""
    user_id = get_user_id(request)
    return await latency_heatmap(
        user_id, bounds.window_hours, since=bounds.since, until=bounds.until
    )


@router.get("/api/monitoring/latency-scatter")
async def get_latency_scatter(
    request: Request,
    bounds: WindowBounds = Depends(bounded_window),
    limit: int = Query(1000, ge=1, le=5000),
) -> Any:
    """Bounded newest-first sample of retrievals: hit-count vs latency."""
    user_id = get_user_id(request)
    return await latency_scatter(
        user_id,
        bounds.window_hours,
        limit=limit,
        since=bounds.since,
        until=bounds.until,
    )
