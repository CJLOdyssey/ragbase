"""Run/message serializers — ORM rows → API dicts."""

from typing import Any


def serialize_message(m: Any) -> dict[str, Any]:
    """Serialize a chat message row for API responses."""
    return {
        "id": m.id,
        "role": m.role,
        "agent_name": m.agent_name,
        "content": m.content,
        "thinking": m.thinking,
        "round_number": m.round_number,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


def serialize_run(run: Any, messages: list[Any] | None = None) -> dict[str, Any]:
    """Serialize a run row (with optional messages) for API responses."""
    data: dict[str, Any] = {
        "id": run.id,
        "session_id": run.session_id,
        "requirement": run.requirement,
        "pm_document": run.pm_document,
        "code": run.code,
        "review": run.review,
        "approved": run.approved,
        "status": run.status,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None,
    }
    if messages is not None:
        data["messages"] = [serialize_message(m) for m in messages]
    return data
