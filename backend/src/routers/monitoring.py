"""Online quality monitoring routes — R3 metrics + alerts (ENTERPRISE_RAG_TOP_BAR §4 #7).

Exposes per-user retrieval/feedback aggregates over a sliding window plus
threshold-based alerts. Purely read-only; metrics feed the frontend panel.
"""

from typing import Any

from auth import get_user_id
from fastapi import APIRouter, Query, Request
from repository.monitoring import evaluate_alerts, feedback_summary, retrieval_summary

router = APIRouter(tags=["monitoring"])


@router.get("/api/monitoring/summary")
async def get_quality_summary(
    request: Request,
    window_hours: int = Query(24, ge=1, le=24 * 30),
    max_empty_recall_pct: float = Query(15.0, ge=0, le=100),
    max_p95_latency_ms: int = Query(8000, ge=1),
    min_good_ratio: float = Query(0.6, ge=0, le=1),
) -> Any:
    """Aggregate retrieval/feedback quality metrics with alerts for the window."""
    user_id = get_user_id(request)
    retrieval = await retrieval_summary(user_id, window_hours)
    feedback = await feedback_summary(user_id, window_hours)
    alerts = evaluate_alerts(
        retrieval,
        feedback,
        max_empty_recall_pct=max_empty_recall_pct,
        max_p95_latency_ms=max_p95_latency_ms,
        min_good_ratio=min_good_ratio,
    )
    return {
        "window_hours": window_hours,
        "retrieval": retrieval,
        "feedback": feedback,
        "alerts": alerts,
    }
