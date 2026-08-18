"""Prompt CRUD API routes.

Prompts are a GLOBAL shared resource (not per-user): unlike assets/monitoring,
no user isolation applies — every authenticated user sees the same library.
Auth is enforced by AuthMiddleware; get_user_id is intentionally unused here.
"""

from typing import Any

from core.audit import log_audit
from core.error_codes import ErrorCode, error_response
from core.infra.logging_config import get_logger
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from repository import create_prompt, delete_prompt, get_prompts_as_dicts, update_prompt
from repository.prompts import PromptRepository
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)
router = APIRouter(tags=["prompts"])


class PromptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    description: str = ""
    category: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    model: str | None = None
    status: str | None = None


class PromptUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    content: str | None = None
    model: str | None = None
    status: str | None = None


@router.get("/api/prompts/categories")
async def list_prompt_categories() -> Any:
    return [
        {"value": "system", "label": "系统提示词"},
        {"value": "user", "label": "用户提示词"},
        {"value": "meta", "label": "元提示词"},
    ]


@router.get("/api/prompts")
async def list_prompts(category: str | None = None) -> Any:
    """List all prompts, optionally filtered by category."""
    try:
        prompts = await get_prompts_as_dicts()
        if category:
            prompts = [p for p in prompts if p["category"] == category]
        return prompts
    except Exception as e:
        logger.error("Error listing prompts: %s", e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR) from e


async def _snapshot_prompt(resource_id: str, session: AsyncSession | None = None) -> Any:
    """Create a version snapshot after prompt save."""
    try:
        from repository.snapshot_helper import build_table_snapshot, with_session
        from repository.versions import create_version as _cv

        async def _save(s: Any, rt: str, rid: str, **kw: Any) -> None:
            from repository.prompts import get_prompt
            item = await get_prompt(rid)
            if not item:
                return
            snapshot = build_table_snapshot(item)
            await _cv(s, rt, rid, snapshot, "system")

        await with_session(
            _save,
            resource_type="prompt",
            resource_id=resource_id,
            session=session,
        )
    except Exception:
        logger.warning("Version snapshot failed for prompt %s", resource_id, exc_info=True)

@router.post("/api/prompts", status_code=201)
async def add_prompt(req: PromptCreate) -> Any:
    """Create a new prompt."""
    try:
        p = await create_prompt(req.model_dump())
        await _snapshot_prompt(p.id)
        await log_audit("create", "prompt", p.name, "创建成功")
        return PromptRepository.to_dict(p)
    except Exception as e:
        logger.error("Error creating prompt: %s", e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR) from e


@router.put("/api/prompts/{prompt_id}")
async def edit_prompt(prompt_id: str, req: PromptUpdate) -> Any:
    """Update an existing prompt."""
    try:
        p = await update_prompt(prompt_id, req.model_dump(exclude_unset=True))
        if not p:
            raise error_response(ErrorCode.PROMPT_NOT_FOUND, detail="Prompt not found")
        await _snapshot_prompt(prompt_id)
        await log_audit("update", "prompt", p.name, "更新成功")
        return PromptRepository.to_dict(p)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating prompt: %s", e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR) from e


@router.delete("/api/prompts/{prompt_id}", status_code=204)
async def remove_prompt(prompt_id: str) -> None:
    """Delete a prompt by ID."""
    try:
        from repository import get_prompt
        target = await get_prompt(prompt_id)
        prompt_name = target.name if target else prompt_id
        ok = await delete_prompt(prompt_id)
        if not ok:
            raise error_response(ErrorCode.PROMPT_NOT_FOUND, detail="Prompt not found")
        await log_audit("delete", "prompt", prompt_name, "删除成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting prompt: %s", e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR) from e
