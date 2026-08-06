"""Session aggregation domain logic — edit-chain folding & requirement prepend.

Extracted from routers/sessions.py so HTTP layer stays thin.
"""

from typing import Any

from .text_utils import parse_json_list


def with_requirement_message(run: Any, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prepend the run requirement as a synthetic user message when the run has
    no persisted user message. chat_messages only stores assistant/agent turns;
    the user prompt lives on the run's ``requirement`` field."""
    if any(m.get("role") == "user" for m in messages):
        return messages
    req = (run.requirement or "").strip()
    if not req:
        return messages
    return [
        {
            "id": f"run-{run.id}-requirement",
            "role": "user",
            "agent_name": "我",
            "content": req,
            "thinking": None,
            "round_number": 0,
            "created_at": None,
            "user_versions": parse_json_list(getattr(run, "requirement_versions", None)),
        },
        *messages,
    ]


def merge_edit_chains(
    runs: list[Any], messages_by_run: dict[str, list[dict[str, Any]]]
) -> list[tuple[Any, list[dict[str, Any]]]]:
    """Fold edit-regenerate runs so only the newest run of each chain is shown.

    Edit-regenerating a user message creates a NEW run whose ``parent_run_id``
    points at the replaced run. Groups every run sharing a common root and
    displays only the newest one, folding older answers into ``versions``."""
    by_id = {r.id: r for r in runs}
    groups: dict[str, list[Any]] = {}
    for r in runs:
        root = r
        while root.parent_run_id and root.parent_run_id in by_id:
            root = by_id[root.parent_run_id]
        groups.setdefault(root.id, []).append(r)

    result: list[tuple[Any, list[dict[str, Any]]]] = []
    for group in groups.values():
        group.sort(key=lambda x: x.created_at)
        latest = group[-1]
        msgs = [dict(m) for m in messages_by_run.get(latest.id, [])]
        versions: list[str] = []
        thinking_versions: list[str] = []
        for cr in group[:-1]:
            hist = [m for m in messages_by_run.get(cr.id, []) if m.get("role") != "user"]
            if hist:
                versions.append(hist[-1].get("content", ""))
                thinking_versions.append(hist[-1].get("thinking") or "")
        if versions and msgs:
            agent_idx = next((i for i, m in enumerate(msgs) if m.get("role") != "user"), -1)
            if agent_idx >= 0:
                msgs[agent_idx]["versions"] = versions + list(msgs[agent_idx].get("versions") or [])
                msgs[agent_idx]["thinking_versions"] = (
                    thinking_versions + list(msgs[agent_idx].get("thinking_versions") or [])
                )
        result.append((latest, msgs))
    return result


__all__ = ["with_requirement_message", "merge_edit_chains"]
