"""Shared text parsing helpers (no business logic)."""

import json


def parse_json_list(raw: str | None) -> list[str] | None:
    """Parse a JSON array string into a list; None on empty/invalid."""
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else None
    except Exception:
        return None


__all__ = ["parse_json_list"]
