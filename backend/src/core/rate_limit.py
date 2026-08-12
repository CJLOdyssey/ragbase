"""Per-user sliding-window rate limiter for LLM-consuming endpoints (OWASP LLM10).

In-process only — single backend process. Multi-instance deployments must
back this with a shared store (Redis); documented limitation.
"""

import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    def __init__(self, max_calls: int, window_seconds: int) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        """Record a hit and return False when the window is exhausted."""
        current = now if now is not None else time.monotonic()
        hits = self._hits[key]
        cutoff = current - self.window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= self.max_calls:
            return False
        hits.append(current)
        return True
