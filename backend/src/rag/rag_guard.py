"""Pre-index document guard — OWASP LLM08 (Vector & Embedding Weaknesses).

Rejects text that must never reach the vector store: zero-width/control
characters (hidden-text smuggling) and high-precision prompt-injection
markers. Precision over recall: a legit document must never be blocked, so
the marker list is deliberately small and hand-picked (classic injection
phrases only — not bare words like "system prompt", which occur in legit
guides). The full OWASP control set is: validate before indexing, ingest
only trusted sources; this module implements the content half, and
ALLOWED_INDEX_SOURCES the source whitelist half.
"""

import re

# Zero-width / bidi override / control chars that carry no visible glyph —
# the classic hidden-text smuggling vector (white-on-white text, invisible
# instructions). C0 controls except \n \r \t, C1, zero-width joiners/spaces,
# bidi overrides/isolates, BOM.
_CONTROL_CHARS = re.compile(
    "[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\u0080-\u009f"
    "\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]"
)

# High-precision prompt-injection phrases (lowercased for matching).
_INSTRUCTION_MARKERS: tuple[str, ...] = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "ignore all previous prompts",
    "ignore the system prompt",
    "disregard the above",
    "disregard previous instructions",
    "override your instructions",
    "hidden instruction",
    "secret instruction",
    "忽略以上所有内容",
    "忽略以上指令",
    "忽略之前所有指令",
    "忽略之前的指令",
    "忽略先前指令",
    "无视以上指令",
    "忽略你的系统提示",
)

# Sources that may enter the index. Future connectors (sharepoint/s3/db/dir)
# must be added here at their own ingestion boundary, not silently.
ALLOWED_INDEX_SOURCES = frozenset({"upload", "url"})


def scan_document(text: str) -> list[str]:
    """Return human-readable rejection reasons (empty = clean)."""
    reasons: list[str] = []
    control = _CONTROL_CHARS.findall(text)
    if control:
        reasons.append(f"contains {len(control)} zero-width/control character(s)")
    lowered = text.lower()
    for marker in _INSTRUCTION_MARKERS:
        if marker in lowered:
            reasons.append(f"contains instruction marker: {marker!r}")
    return reasons


_REDACTION = "[已过滤]"


def sanitize_context(text: str) -> str:
    """Deterministically neutralize untrusted retrieved text before injection.

    Strips zero-width/control characters and replaces high-precision
    instruction markers with an inert placeholder. The model never sees the
    instruction text, so compliance does not depend on prompt instructions
    (prompt text is a soft layer; this is the hard one — OWASP LLM01
    "validate/scrub documents" applied at the injection boundary).
    """
    cleaned = _CONTROL_CHARS.sub("", text)
    for marker in _INSTRUCTION_MARKERS:
        cleaned = re.sub(re.escape(marker), _REDACTION, cleaned, flags=re.IGNORECASE)
    return cleaned
