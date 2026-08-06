"""Run API routes: create, list, detail, and WebSocket streaming."""

import contextlib
import time
from typing import Any

from auth import get_user_id
from broker import drain_buffer, stop_buffer, subscribe_run
from core.config import load_config
from core.error_codes import ErrorCode, error_response
from core.infra.logging_config import get_logger
from core.models import RunDetail, RunSummary
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel
from repository import get_messages, get_run
from services.run_service import run_service

logger = get_logger(__name__)
router = APIRouter(tags=["runs"])

_MAX_REQUIREMENT_LENGTH = 2000


class RunRequest(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    requirement: str = Field(..., min_length=1, max_length=_MAX_REQUIREMENT_LENGTH)
    session_id: str | None = None
    key_id: str | None = Field(
        default=None, description="Vaulted API key ID — server resolves key, never exposes it"
    )
    model: str | None = None
    parent_run_id: str | None = None


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
    try:
        result = await run_service.create_run(
            requirement=requirement,
            session_id=req.session_id,
            user_id=user_id,
            key_id=req.key_id,
            model=req.model,
            parent_run_id=req.parent_run_id,
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
async def get_run_detail(run_id: str) -> Any:
    """Get detailed information for a specific run."""
    try:
        result = await run_service.get_run(run_id)
        if result is None:
            raise error_response(ErrorCode.RUN_NOT_FOUND, detail="未找到该次讨论")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching run %s: %s", run_id, e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR) from e


@router.get("/api/runs", response_model=list[RunSummary])
async def list_runs(limit: int = 20) -> Any:
    """List recent runs with a configurable limit."""
    try:
        return await run_service.list_runs(limit=limit)
    except Exception as e:
        logger.error("Error listing runs: %s", e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR) from e


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
    try:
        await websocket.send_json({"type": "status", "status": "connected"})

        # Check if run already completed (race condition: task finished before WS connected)
        try:
            run = await get_run(run_id)
            if run and run.status in ("converged", "error"):
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
