"""LLM billing/quota error detection — shared by the graph engine and task pipeline.

Both ``graph/helpers._is_balance_error`` (HTTP error body from the streaming
call) and ``tasks/pipeline_utils._is_balance_error`` (raised exception) were
duplicated keyword lists; this module is the single source of truth.
"""

from __future__ import annotations

# Balance/quota error keywords used to detect API billing failures. Providers
# (DeepSeek/SiliconFlow/OpenAI) return varying phrasing; keep the match
# substring-based and case-insensitive so 402/余额不足/insufficient_quota etc.
# all surface a "balance" signal to the frontend.
BALANCE_ERROR_KEYWORDS = [
    "insufficient_quota",
    "insufficient_balance",
    "insufficient balance",
    "余额不足",
    "billing limit",
    "quota exceeded",
    "payment required",
    "account balance",
    "402",
]


def is_balance_error(text: str) -> bool:
    """Return True when ``text`` mentions insufficient model balance/quota.

    Args:
        text: Error body or exception message (matched case-insensitively).
    """
    lowered = text.lower()
    return any(kw in lowered for kw in BALANCE_ERROR_KEYWORDS)
