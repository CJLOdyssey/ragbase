"""Run API routes: create, list, detail, and WebSocket streaming."""

import contextlib
import json
import time
from typing import Any

from auth import get_user_id
from auth.auth_jwt import AUTH_SECRET, decode_jwt
from broker import drain_buffer, stop_buffer, subscribe_run
from core.config import load_config
from core.error_codes import ErrorCode, error_response
from core.infra.logging_config import get_logger
from core.models import RunDetail, RunSummary
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel
from repository import get_messages, get_run_for_user
from services.run_service import run_service

from routers.run_limits import run_limiter

logger = get_logger(__name__)
router = APIRouter(tags=["runs"])

_MAX_REQUIREMENT_LENGTH = 2000


def _parse_sources(raw: str | None) -> list[dict[str, Any]]:
    """Deserialize the chat_messages.sources JSON column; malformed → empty."""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


class RunRequest(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    requirement: str = Field(..., min_length=1, max_length=_MAX_REQUIREMENT_LENGTH)
    session_id: str | None = None
    key_id: str | None = Field(
        default=None, description="Vaulted API key ID — server resolves key, never exposes it"
    )
    model: str | None = None
    parent_run_id: str | None = None
    attachment_ids: list[str] | None = None
    prompt_id: str | None = Field(
        default=None,
        description="启用(active)提示词 ID — 作为对话人设注入；草稿不生效",
    )


class RunResponse(BaseModel):
    run_id: str
    status: str
    session_id: str | None = None


@router.post("/api/runs", response_model=RunResponse)
async def create_run(req: RunRequest, request: Request) -> Any:
    """Create and start a new agent run."""
    requirement = req.requirement.strip()
    config = load_config()
    if len(requirement) > config.max_requirement_length:
        raise error_response(
            ErrorCode.INVALID_REQUEST, detail=f"需求不能超过 {config.max_requirement_length} 字"
        )
    if not requirement:
        raise error_response(ErrorCode.INVALID_REQUEST, detail="需求不能为空")

    user_id = get_user_id(request)
    if not run_limiter.allow(user_id):
        raise error_response(
            ErrorCode.RATE_LIMITED, detail="请求过于频繁，请稍后再试"
        )
    try:
        result = await run_service.create_run(
            requirement=requirement,
            session_id=req.session_id,
            user_id=user_id,
            key_id=req.key_id,
            model=req.model,
            parent_run_id=req.parent_run_id,
            attachment_ids=req.attachment_ids,
            prompt_id=req.prompt_id,
        )
        return RunResponse(**result)
    except ValueError as e:
        raise error_response(ErrorCode.INVALID_REQUEST, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create run: %s", e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR, detail=f"执行失败: {e}") from e


@router.get("/api/runs/{run_id}", response_model=RunDetail)
async def get_run_detail(run_id: str, request: Request) -> Any:
    """Get detailed information for a specific run (owner-scoped)."""
    try:
        result = await run_service.get_run(run_id, get_user_id(request))
        if result is None:
            raise error_response(ErrorCode.RUN_NOT_FOUND, detail="未找到该次讨论")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching run %s: %s", run_id, e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR) from e


@router.get("/api/runs", response_model=list[RunSummary])
async def list_runs(request: Request, limit: int = 20) -> Any:
    """List the current user's recent runs with a configurable limit."""
    try:
        return await run_service.list_runs(limit=limit, user_id=get_user_id(request))
    except Exception as e:
        logger.error("Error listing runs: %s", e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR) from e


@router.post("/api/runs/{run_id}/cancel", response_model=RunResponse)
async def cancel_run(run_id: str, request: Request) -> Any:
    """Cancel an in-flight run (owner-scoped): propagate cancellation to the LLM stream."""
    try:
        result = await run_service.cancel_run(run_id, get_user_id(request))
        if result.get("status") == "not_found":
            raise error_response(ErrorCode.RUN_NOT_FOUND, detail="未找到该次讨论")
        return RunResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error cancelling run %s: %s", run_id, e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR) from e


def _ws_user_id(websocket: WebSocket) -> str:
    """Resolve user identity from the WS handshake (cookie, then ?token=).

    AuthMiddleware exempts the ``/ws/`` prefix (WebSockets can't set headers
    cross-origin), so this endpoint must authenticate itself — mirror of
    ``routers/events.py:_ws_user_id``.
    """
    token = websocket.cookies.get("access_token") or ""
    logger.warning("WS cookies: %s", dict(websocket.cookies))
    if not token:
        token = websocket.query_params.get("token", "")
    if not token:
        return ""
    payload = decode_jwt(token, AUTH_SECRET)
    if payload:
        uid = payload.get("sub")
        if isinstance(uid, str) and uid:
            return uid
    return ""


async def _reject(websocket: WebSocket, message: str) -> None:
    """Send a terminal error status and close the socket (auth/ownership fail)."""
    with contextlib.suppress(Exception):
        await websocket.send_json({"type": "status", "status": "error", "error": message})
    with contextlib.suppress(Exception):
        await websocket.close(code=1008)


@router.websocket("/ws/runs/{run_id}")
async def run_websocket(websocket: WebSocket, run_id: str) -> Any:
    """Stream run progress and messages over a WebSocket connection."""
    client_host = websocket.client.host if websocket.client else "?"
    await websocket.accept()
    logger.info(
        "WebSocket connected | run_id=%s | client=%s",
        run_id, client_host,
    )
    _ws_t0 = time.monotonic()

    # AuthMiddleware exempts /ws/*; authenticate + authorize here or the
    # stream leaks any run's content to unauthenticated callers.
    user_id = _ws_user_id(websocket)
    if not user_id:
        logger.warning("WS rejected (unauthenticated) | run_id=%s | client=%s", run_id, client_host)
        await _reject(websocket, "未登录")
        return
    run = await get_run_for_user(run_id, user_id)
    if run is None:
        logger.warning("WS rejected (not owner) | run_id=%s | client=%s", run_id, client_host)
        await _reject(websocket, "无权访问该运行")
        return

    try:
        await websocket.send_json({"type": "status", "status": "connected"})

        # Check if run already completed (race condition: task finished before WS connected)
        try:
            if run.status in ("converged", "error"):
                await stop_buffer(run_id)
                messages = await get_messages(run_id)
                for m in messages:
                    await websocket.send_json(
                        {
                            "type": "message",
                            "role": m.role,
                            "agent_name": m.agent_name,
                            "content": m.content,
                            "round_number": m.round_number,
                            "sources": _parse_sources(m.sources),
                        }
                    )
                await websocket.send_json(
                    {
                        "type": "result",
                        "status": run.status,
                        "approved": run.approved,
                        "pm_document": run.pm_document or "",
                        "code": run.code or "",
                        "review": run.review or "",
                    }
                )
                await websocket.close()
                return
        except Exception as e:
            logger.warning("Pre-check run status failed: %s", e)

        try:
            for msg in drain_buffer(run_id):
                try:
                    await websocket.send_json(msg)
                except WebSocketDisconnect:
                    return

            async for message in subscribe_run(run_id):
                try:
                    await websocket.send_json(message)
                except WebSocketDisconnect:
                    elapsed = time.monotonic() - _ws_t0
                    logger.info(
                        "WebSocket disconnected | run_id=%s | client=%s | elapsed=%.1fs",
                        run_id, client_host, elapsed,
                    )
                    return
                except Exception as e:
                    logger.warning(
                        "WebSocket send error | run_id=%s | client=%s | error=%s",
                        run_id, client_host, e,
                    )
                    return
        except Exception as e:
            logger.error("Redis subscribe error: %s", e, exc_info=True)
            with contextlib.suppress(Exception):
                await websocket.send_json({"type": "status", "status": "error", "error": str(e)})
        finally:
            await stop_buffer(run_id)
    except WebSocketDisconnect:
        elapsed = time.monotonic() - _ws_t0
        logger.info(
            "WebSocket disconnected gracefully | run_id=%s | client=%s | elapsed=%.1fs",
            run_id, client_host, elapsed,
        )
    except Exception as e:
        elapsed = time.monotonic() - _ws_t0
        logger.error(
            "WebSocket error | run_id=%s | client=%s | elapsed=%.1fs | error=%s",
            run_id, client_host, elapsed, e, exc_info=True,
        )
