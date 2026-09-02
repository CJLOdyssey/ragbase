"""Per-user sliding-window rate limiter for LLM-consuming endpoints (OWASP LLM10).

In-process only — single backend process. Multi-instance deployments must
back this with a shared store (Redis); documented limitation.
"""

import time
from collections import defaultdict, deque

# Above this many tracked keys, expired entries are swept on the next call.
_SWEEP_THRESHOLD = 10_000


class SlidingWindowLimiter:
    def __init__(self, max_calls: int, window_seconds: int) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        """Record a hit and return False when the window is exhausted."""
        current = now if now is not None else time.monotonic()
        if len(self._hits) >= _SWEEP_THRESHOLD:
            self._sweep(current)

        hits = self._hits[key]
        cutoff = current - self.window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if not hits:
            # Drop the idle key so its entry doesn't persist across windows,
            # then re-fetch so the new hit registers under a fresh entry.
            self._hits.pop(key, None)
            hits = self._hits[key]
        if len(hits) >= self.max_calls:
            return False
        hits.append(current)
        return True

    def _sweep(self, current: float) -> None:
        """Drop every key whose most recent hit is already outside the window."""
        cutoff = current - self.window_seconds
        expired = [key for key, hits in self._hits.items() if not hits or hits[-1] <= cutoff]
        for key in expired:
            del self._hits[key]
