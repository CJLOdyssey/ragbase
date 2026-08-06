"""Unit tests for session_service domain logic (edit-chain folding)."""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from services.session_service import merge_edit_chains, with_requirement_message


def _run(run_id: str, parent: str | None = None, requirement: str = "需求") -> Any:
    return SimpleNamespace(id=run_id, parent_run_id=parent, requirement=requirement,
                           created_at=datetime.now(UTC))


def _msg(run_id: str, role: str, content: str) -> dict[str, Any]:
    return {"id": f"m-{run_id}", "role": role, "content": content, "thinking": None}


def test_fold_shows_only_latest_of_chain():
    r1 = _run("r1")
    r2 = _run("r2", parent="r1")
    result = merge_edit_chains([r1, r2], {"r1": [_msg("r1", "agent", "旧答案")],
                                          "r2": [_msg("r2", "agent", "新答案")]})
    assert len(result) == 1
    latest, msgs = result[0]
    assert latest.id == "r2"
    assert msgs[0]["versions"] == ["旧答案"]


def test_requirement_prepended_when_no_user_message():
    run = _run("r1")
    msgs = [_msg("r1", "agent", "答案")]
    out = with_requirement_message(run, msgs)
    assert out[0]["role"] == "user"
    assert out[0]["content"] == "需求"


def test_requirement_not_prepended_when_user_message_exists():
    run = _run("r1")
    msgs = [_msg("r1", "user", "用户原话"), _msg("r1", "agent", "答案")]
    out = with_requirement_message(run, msgs)
    assert out == msgs
