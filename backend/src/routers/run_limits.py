"""Shared run-creation rate limiter — OWASP LLM10 unbounded-consumption guard.

Used by both the primary run endpoint (``routers/runs.py``) and the
continuation endpoint (``routers/run_continue.py``) so every LLM-triggering
route is throttled per user with one consistent budget.

In-process window; multi-instance deployments need a shared store (the
in-memory scope is documented next to ``SlidingWindowLimiter``).
"""

import os

from core.rate_limit import SlidingWindowLimiter

run_limiter = SlidingWindowLimiter(
    max_calls=int(os.environ.get("RUN_RATE_LIMIT_PER_MIN", "6")),
    window_seconds=60,
)

__all__ = ["run_limiter"]
