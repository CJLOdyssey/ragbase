"""Bad-feedback review queue routes — human triage of low-quality answers."""

from typing import Any

from auth import get_user_id
from core.error_codes import ErrorCode, error_response
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel
from repository.feedback_review import list_bad_feedback, upsert_review

from routers.window_range import WindowBounds, bounded_window

router = APIRouter(tags=["monitoring"])


class BadFeedbackItem(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    feedback_id: str
    run_id: str
    query: str | None
    answer: str | None
    created_at: str | None
    review: dict[str, Any] | None


class BadFeedbackResponse(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    items: list[BadFeedbackItem]
    total: int
    page: int
    page_size: int


class ReviewUpsertIn(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    status: str = Field(pattern="^(pending|resolved|dismissed)$")
    root_cause: str | None = Field(
        default=None,
        pattern="^(retrieval_miss|wrong_answer|bad_format|other)$",
    )
    note: str | None = None


@router.get("/api/monitoring/bad-feedback", response_model=BadFeedbackResponse)
async def get_bad_feedback(
    request: Request,
    bounds: WindowBounds = Depends(bounded_window),
    status: str | None = Query(
        None, pattern="^(pending|resolved|dismissed)$"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Any:
    """List bad-rated feedback (optionally filtered by triage status)."""
    user_id = get_user_id(request)
    items, total = await list_bad_feedback(
        user_id=user_id,
        window_hours=bounds.window_hours,
        status=status,
        page=page,
        page_size=page_size,
        since=bounds.since,
        until=bounds.until,
    )
    return BadFeedbackResponse(
        items=[BadFeedbackItem(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/api/monitoring/bad-feedback/{feedback_id}/review")
async def review_bad_feedback(
    feedback_id: str,
    body: ReviewUpsertIn,
    request: Request,
) -> Any:
    """Create/update the triage record for one bad rating."""
    user_id = get_user_id(request)
    result = await upsert_review(
        user_id=user_id,
        feedback_id=feedback_id,
        status=body.status,
        root_cause=body.root_cause,
        note=body.note,
    )
    if result is None:
        raise error_response(ErrorCode.REVIEW_NOT_FOUND, detail="记录不存在")
    return result
