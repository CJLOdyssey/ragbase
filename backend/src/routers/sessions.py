"""Session and Memory API routes."""

import json
import time
from typing import Any

from auth import get_user_id
from broker import publish_user_event
from core.error_codes import ErrorCode, error_response
from core.infra.logging_config import get_logger
from core.models import AttachmentResponse, SessionDetailResponse, SessionSummary
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from repository import (
    create_session,
    delete_memory_entry,
    delete_session,
    delete_vector_chunks_by_session,
    get_runs_by_session_ids,
    get_session,
    get_session_memories,
    get_session_messages,
    get_session_runs,
    get_sessions,
    update_session_pin,
    update_session_title,
)
from repository.attachments import list_attachments_by_session
from services.session_service import with_requirement_message
from services.text_utils import parse_json_list
from starlette.responses import Response

logger = get_logger(__name__)

router = APIRouter(tags=["sessions"])


async def _publish_session_event(user_id: str, event_type: str, session_id: str) -> None:
    """Notify the user's other clients that a session changed (fail-open)."""
    await publish_user_event(
        user_id,
        {"type": event_type, "session_id": session_id, "ts": int(time.time())},
    )


class SessionCreateRequest(BaseModel):
    title: str = "新对话"


class SessionUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)


class SessionPinRequest(BaseModel):
    is_pinned: bool = True


@router.get("/api/sessions", response_model=list[SessionSummary])
async def list_sessions(request: Request, limit: int = 50) -> Any:
    """List sessions for the current user."""
    try:
        user_id = get_user_id(request)
        sessions = await get_sessions(limit=min(limit, 100), user_id=user_id)
        session_ids = [s.id for s in sessions]
        runs_by_session = await get_runs_by_session_ids(session_ids)
        result = []
        for s in sessions:
            runs = runs_by_session.get(s.id, [])
            result.append(
                {
                    "id": s.id,
                    "title": s.title,
                    "kind": s.kind,
                    "run_count": len(runs),
                    "is_pinned": s.is_pinned,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                }
            )
        return result
    except Exception as e:
        logger.error("Error listing sessions: %s", e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR) from e


@router.post("/api/sessions", status_code=201)
async def add_session(request: Request, req: SessionCreateRequest) -> Any:
    """Create a new chat session."""
    try:
        user_id = get_user_id(request)
        sess = await create_session(title=req.title, user_id=user_id)
        await _publish_session_event(user_id, "session.created", sess.id)
        return {
            "id": sess.id,
            "title": sess.title,
            "created_at": sess.created_at.isoformat() if sess.created_at else None,
            "updated_at": sess.updated_at.isoformat() if sess.updated_at else None,
        }
    except Exception as e:
        logger.error("Error creating session: %s", e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR) from e


@router.get("/api/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(request: Request, session_id: str) -> Any:
    """Get full session detail including runs and memories."""
    try:
        user_id = get_user_id(request)
        sess = await get_session(session_id)
        if not sess:
            raise error_response(ErrorCode.SESSION_NOT_FOUND, detail="未找到该对话")
        if sess.user_id != user_id:
            raise error_response(ErrorCode.SESSION_FORBIDDEN, detail="无权访问该对话")

        runs = await get_session_runs(session_id)
        memories = await get_session_memories(session_id)

        # Attachments by run: 让前端在用户消息里展示文件（下载链接）。
        # 附件经 POST /runs 绑定 run_id（选中即传仅带 session_id）。
        attachments_by_run: dict[str, list[AttachmentResponse]] = {}
        try:
            atts = await list_attachments_by_session(session_id)
            for a in atts:
                if not a.run_id:
                    continue
                attachments_by_run.setdefault(a.run_id, []).append(
                    AttachmentResponse(
                        id=a.id,
                        session_id=a.session_id,
                        run_id=a.run_id,
                        filename=a.filename,
                        content_type=a.content_type,
                        size_bytes=a.size_bytes,
                        has_extracted_text=bool(a.extracted_text),
                        created_at=a.created_at,
                    )
                )
        except Exception:
            logger.warning("Failed to load attachments for session %s", session_id)

        # Load messages with thinking for all runs in batch
        all_messages = await get_session_messages(session_id)
        messages_by_run: dict[str, list[dict[str, Any]]] = {}
        for m in all_messages:
            if m.run_id not in messages_by_run:
                messages_by_run[m.run_id] = []
            messages_by_run[m.run_id].append({
                "id": m.id,
                "role": m.role,
                "agent_name": m.agent_name,
                "content": m.content,
                "thinking": m.thinking,
                "round_number": m.round_number,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            })

        # 分支树模型：不折叠。每个 run 独立返回（parent_run_id 为树指针），
        # 前端按"根→选中 run 路径"渲染视图。
        merged = [(r, with_requirement_message(r, messages_by_run.get(r.id, []))) for r in runs]

        return {
            "id": sess.id,
            "title": sess.title,
            "kind": sess.kind,
            "created_at": sess.created_at.isoformat() if sess.created_at else None,
            "updated_at": sess.updated_at.isoformat() if sess.updated_at else None,
            "runs": [
                {
                    "id": r.id,
                    "requirement": r.requirement,
                    "pm_document": r.pm_document,
                    "code": r.code,
                    "review": r.review,
                    "approved": r.approved,
                    "status": r.status,
                    "parent_run_id": r.parent_run_id,
                    "requirement_versions": parse_json_list(r.requirement_versions),
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                    "messages": with_requirement_message(r, msgs),
                    "attachments": attachments_by_run.get(r.id, []),
                }
                for r, msgs in merged
            ],
            "memories": [
                {
                    "id": m.id,
                    "agent_role": m.agent_role,
                    "content_type": m.content_type,
                    "summary": m.summary,
                    "details": m.details,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in memories
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting session %s: %s", session_id, e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR) from e


@router.put("/api/sessions/{session_id}")
async def rename_session(request: Request, session_id: str, req: SessionUpdateRequest) -> Any:
    """Rename a session's title."""
    try:
        user_id = get_user_id(request)
        sess = await get_session(session_id)
        if not sess:
            raise error_response(ErrorCode.SESSION_NOT_FOUND, detail="未找到该对话")
        if sess.user_id != user_id:
            raise error_response(ErrorCode.SESSION_FORBIDDEN, detail="无权修改该对话")
        sess = await update_session_title(session_id, req.title)
        if not sess:
            raise error_response(ErrorCode.SESSION_NOT_FOUND, detail="未找到该对话")
        await _publish_session_event(user_id, "session.updated", session_id)
        return {"id": sess.id, "title": sess.title, "status": "updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error renaming session %s: %s", session_id, e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR) from e


@router.put("/api/sessions/{session_id}/pin")
async def pin_session(request: Request, session_id: str, req: SessionPinRequest) -> Any:
    """Pin or unpin a session for sidebar pin-to-top."""
    try:
        user_id = get_user_id(request)
        sess = await get_session(session_id)
        if not sess:
            raise error_response(ErrorCode.SESSION_NOT_FOUND, detail="未找到该对话")
        if sess.user_id != user_id:
            raise error_response(ErrorCode.SESSION_FORBIDDEN, detail="无权修改该对话")
        sess = await update_session_pin(session_id, req.is_pinned)
        if not sess:
            raise error_response(ErrorCode.SESSION_NOT_FOUND, detail="未找到该对话")
        await _publish_session_event(user_id, "session.updated", session_id)
        return {"id": sess.id, "is_pinned": sess.is_pinned, "status": "updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error pinning session %s: %s", session_id, e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR) from e


@router.delete("/api/sessions/{session_id}")
async def remove_session(request: Request, session_id: str) -> Any:
    """Delete a session and its associated data."""
    try:
        user_id = get_user_id(request)
        sess = await get_session(session_id)
        if not sess:
            raise error_response(ErrorCode.SESSION_NOT_FOUND, detail="未找到该对话")
        if sess.user_id != user_id:
            raise error_response(ErrorCode.SESSION_FORBIDDEN, detail="无权删除该对话")
        deleted = await delete_session(session_id)
        if not deleted:
            raise error_response(ErrorCode.SESSION_NOT_FOUND, detail="未找到该对话")
        await delete_vector_chunks_by_session(session_id)
        await _publish_session_event(user_id, "session.deleted", session_id)
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting session %s: %s", session_id, e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR) from e


@router.get("/api/sessions/{session_id}/memories")
async def list_session_memories(request: Request, session_id: str) -> Any:
    """List all memory entries for a session."""
    try:
        user_id = get_user_id(request)
        sess = await get_session(session_id)
        if not sess:
            raise error_response(ErrorCode.SESSION_NOT_FOUND, detail="未找到该对话")
        if sess.user_id != user_id:
            raise error_response(ErrorCode.SESSION_FORBIDDEN, detail="无权访问该对话")
        memories = await get_session_memories(session_id)
        return [
            {
                "id": m.id,
                "agent_role": m.agent_role,
                "content_type": m.content_type,
                "summary": m.summary,
                "details": m.details,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in memories
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error listing memories for %s: %s", session_id, e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR) from e


@router.delete("/api/memories/{memory_id}")
async def delete_session_memory(memory_id: str) -> Any:
    """Delete a single memory entry."""
    try:
        deleted = await delete_memory_entry(memory_id)
        if not deleted:
            raise error_response(ErrorCode.MEMORY_NOT_FOUND, detail="未找到该记忆")
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting memory %s: %s", memory_id, e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR) from e


@router.get("/api/sessions/{session_id}/memories/export")
async def export_session_memories(request: Request, session_id: str, format: str = "json") -> Any:
    """Export session memories as JSON or Markdown."""
    try:
        user_id = get_user_id(request)
        if format not in ("json", "md"):
            raise error_response(ErrorCode.INVALID_REQUEST, detail="format 参数必须为 json 或 md")

        sess = await get_session(session_id)
        if not sess:
            raise error_response(ErrorCode.SESSION_NOT_FOUND, detail="未找到该对话")
        if sess.user_id != user_id:
            raise error_response(ErrorCode.SESSION_FORBIDDEN, detail="无权访问该对话")

        memories = await get_session_memories(session_id)
        items = [
            {
                "id": m.id,
                "agent_role": m.agent_role,
                "content_type": m.content_type,
                "summary": m.summary,
                "details": m.details,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in memories
        ]

        if format == "json":
            content = json.dumps(items, ensure_ascii=False, default=str, indent=2)
            return Response(
                content=content,
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=memories_{session_id}.json"},
            )

        md_lines = [f"# Session Memories ({session_id})\n"]
        for m in memories:
            md_lines.append(f"## Memory: {m.content_type}")
            md_lines.append(

                    f"**Agent**: {m.agent_role} | "
                    f"**Created**: {m.created_at.isoformat() if m.created_at else 'N/A'}"

            )
            md_lines.append("")
            md_lines.append(f"**Summary**: {m.summary}")
            md_lines.append("")
            md_lines.append("**Details**:")
            md_lines.append(m.details or "(无详情)")
            md_lines.append("")
            md_lines.append("---")
            md_lines.append("")
        return Response(
            content="\n".join(md_lines),
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=memories_{session_id}.md"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error exporting memories for %s: %s", session_id, e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR) from e
