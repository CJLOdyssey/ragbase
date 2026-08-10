"""Run quality feedback routes — online eval loop intake."""

from typing import Any

from auth import get_user_id
from core.error_codes import ErrorCode, error_response
from core.infra.logging_config import get_logger
from fastapi import APIRouter, Request
from pydantic import BaseModel
from repository.feedback import create_feedback, list_feedback
from repository.run_repo import get_run_for_user

logger = get_logger(__name__)
router = APIRouter(tags=["feedback"])


class FeedbackIn(BaseModel):
    rating: str


@router.post("/api/runs/{run_id}/feedback", status_code=201)
async def submit_feedback(run_id: str, req: FeedbackIn, request: Request) -> Any:
    """Record answer-quality feedback for a run (good/bad)."""
    user_id = get_user_id(request)
    run = await get_run_for_user(run_id, user_id)
    if run is None:
        raise error_response(ErrorCode.RUN_NOT_FOUND, detail="运行不存在")
    try:
        result = await create_feedback(run_id, user_id, req.rating)
    except ValueError as e:
        raise error_response(ErrorCode.INVALID_REQUEST, detail=str(e)) from e
    logger.info("Feedback recorded | user=%s | run=%s | %s", user_id, run_id, req.rating)
    return result


@router.get("/api/feedback")
async def get_my_feedback(request: Request) -> Any:
    """Export my feedback — the curation channel into the golden set."""
    user_id = get_user_id(request)
    return await list_feedback(user_id)
