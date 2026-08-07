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
    run_ts = getattr(run, "created_at", None)
    return [
        {
            "id": f"run-{run.id}-requirement",
            "role": "user",
            "agent_name": "我",
            "content": req,
            "thinking": None,
            "round_number": 0,
            "created_at": run_ts.isoformat() if run_ts else None,
            "user_versions": parse_json_list(getattr(run, "requirement_versions", None)),
        },
        *messages,
    ]

