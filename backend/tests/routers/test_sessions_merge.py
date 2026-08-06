"""Unit tests for sessions.merge_edit_chains edit-regenerate folding."""

from datetime import datetime
from types import SimpleNamespace

from services.session_service import merge_edit_chains


def _run(run_id: str, parent: str | None = None, created_at: str = "2026-08-02T00:00:00") -> SimpleNamespace:
    return SimpleNamespace(
        id=run_id,
        parent_run_id=parent,
        requirement=f"req-{run_id}",
        requirement_versions=None,
        created_at=datetime.fromisoformat(created_at.replace("Z", "+00:00")),
    )


def _msgs(*contents: str) -> list[dict]:
    return [
        {
            "id": f"msg-{c[:6]}",
            "role": "assistant",
            "agent_name": "Agent",
            "content": c,
            "thinking": f"think-{c[:6]}",
            "round_number": 0,
            "created_at": None,
        }
        for c in contents
    ]


def test_independent_runs_not_folded():
    runs = [_run("a"), _run("b")]
    merged = merge_edit_chains(runs, {"a": _msgs("answer-a"), "b": _msgs("answer-b")})
    assert [r.id for r, _ in merged] == ["a", "b"]
    assert all(len(msgs) == 1 for _, msgs in merged)


def test_linear_chain_folds_into_newest():
    runs = [_run("a"), _run("b", parent="a")]
    merged = merge_edit_chains(runs, {"a": _msgs("answer-a"), "b": _msgs("answer-b")})
    # Only the newest run (b) is shown, with a's answer folded into versions.
    assert len(merged) == 1
    latest, msgs = merged[0]
    assert latest.id == "b"
    agent = [m for m in msgs if m.get("role") != "user"][0]
    assert agent["versions"] == ["answer-a"]
    assert agent["thinking_versions"] == ["think-answer"]


def test_branched_children_fold_into_newest_no_duplicates():
    # A single user message edited twice → two children of run a.
    runs = [
        _run("a", created_at="2026-08-02T10:00:00"),
        _run("b", parent="a", created_at="2026-08-02T11:00:00"),
        _run("c", parent="a", created_at="2026-08-02T12:00:00"),
    ]
    merged = merge_edit_chains(runs, {
        "a": _msgs("answer-a"),
        "b": _msgs("answer-b"),
        "c": _msgs("answer-c"),
    })
    # Both children belong to the same root tree → exactly one display unit (c, the newest).
    assert len(merged) == 1
    latest, msgs = merged[0]
    assert latest.id == "c"
    agent = [m for m in msgs if m.get("role") != "user"][0]
    assert agent["versions"] == ["answer-a", "answer-b"]
    assert agent["thinking_versions"] == ["think-answer", "think-answer"]
