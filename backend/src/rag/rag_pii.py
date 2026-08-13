"""PII detection for LLM output / retrieval context (OWASP LLM02 / S5).

Detection + audit by default: flagged output is logged and surfaced as a
warning event — never silently altered. ``redact_pii`` is provided for
injection-boundary use where redaction is a deliberate product decision.

Patterns are deliberately conservative (high precision, low recall): email /
mainland CN phone / CN 18-digit ID / explicit ``sk-`` API keys. Long random
strings without a marker are NOT flagged — chunks of indexed documents are
full of opaque ids.
"""

import re

PII_TYPES = ("email", "cn_phone", "cn_id", "api_key")

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_CN_PHONE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
_CN_ID = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")
_API_KEY = re.compile(r"(?i)\bsk-[A-Za-z0-9_-]{16,}")

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", _EMAIL),
    ("cn_phone", _CN_PHONE),
    ("cn_id", _CN_ID),
    ("api_key", _API_KEY),
)


def scan_pii(text: str) -> list[dict[str, str]]:
    """Return one entry per detected PII occurrence (deduped by type+match).

    Each entry: {"type": PII_TYPES member, "match": truncated matched text}.
    """
    found: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for ptype, pattern in _PATTERNS:
        for m in pattern.finditer(text):
            key = (ptype, m.group(0))
            if key in seen:
                continue
            seen.add(key)
            found.append({"type": ptype, "match": m.group(0)[:24]})
    return found


def redact_pii(text: str) -> str:
    """Replace detected PII with placeholders: ``[已脱敏:<type>]``."""
    out = text
    for ptype, pattern in _PATTERNS:
        out = pattern.sub(f"[已脱敏:{ptype}]", out)
    return out
