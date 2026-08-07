"""Unit tests for session_service domain logic (requirement prepend)."""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from services.session_service import with_requirement_message


def _run(run_id: str, parent: str | None = None, requirement: str = "需求") -> Any:
    return SimpleNamespace(id=run_id, parent_run_id=parent, requirement=requirement,
                           created_at=datetime.now(UTC))


def _msg(run_id: str, role: str, content: str) -> dict[str, Any]:
    return {"id": f"m-{run_id}", "role": role, "content": content, "thinking": None}


def test_requirement_prepended_when_no_user_message():
    run = _run("r1")
    msgs = [_msg("r1", "agent", "答案")]
    out = with_requirement_message(run, msgs)
    assert out[0]["role"] == "user"
    assert out[0]["content"] == "需求"


def test_requirement_prepended_message_uses_run_timestamp():
    run = _run("r1")
    msgs = [_msg("r1", "agent", "答案")]
    out = with_requirement_message(run, msgs)
    assert out[0]["created_at"] == run.created_at.isoformat()


def test_requirement_not_prepended_when_user_message_exists():
    run = _run("r1")
    msgs = [_msg("r1", "user", "用户原话"), _msg("r1", "agent", "答案")]
    out = with_requirement_message(run, msgs)
    assert out == msgs
