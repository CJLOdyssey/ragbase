"""Run continuation API — "继续生成" feature, runs directly in uvicorn process."""

from typing import Any

from auth import get_user_id
from core.error_codes import ErrorCode, error_response
from core.infra.logging_config import get_logger
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from services.run_service import run_service

from routers.run_limits import run_limiter
from routers.runs import RunResponse

logger = get_logger(__name__)
router = APIRouter(tags=["runs"])


class CompleteRunRequest(BaseModel):
    # content = 被中断消息的正文全文，长度不受控（10MB 请求体中间件兜底），
    # 与 thinking 一致不设上限 —— 设上限会打断长回答的续写。
    content: str = Field(default="")
    session_id: str | None = None
    thinking: str | None = None
    model: str | None = None
    question: str | None = None


@router.post("/api/runs/complete", response_model=RunResponse)
async def create_complete_run(req: CompleteRunRequest, request: Request) -> Any:
    """Create a continuation run — streams raw LLM output without thinking/tools.

    Used by the frontend "继续生成" feature to append content to an interrupted
    agent message without triggering the LangGraph pipeline (no thinking_stream,
    no tool calls, no chat history).
    """
    content = (req.content or "").strip()
    user_id = get_user_id(request)

    if not run_limiter.allow(user_id):
        raise error_response(
            ErrorCode.RATE_LIMITED, detail="请求过于频繁，请稍后再试"
        )

    try:
        result = await run_service.continue_run(
            content=content,
            session_id=req.session_id,
            user_id=user_id,
            thinking=req.thinking,
            model=req.model,
            question=req.question,
        )
        return RunResponse(**result)
    except ValueError as e:
        raise error_response(ErrorCode.INVALID_REQUEST, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Complete pipeline failed for run")
        raise error_response(ErrorCode.INTERNAL_ERROR) from e
