"""Per-IP rate limiting middleware using a fixed-window counter backed by Redis.

Redis failures degrade to an in-process fixed-window counter (same semantics,
per-worker) instead of failing open — an attacker must not be able to bypass
all rate limiting merely by taking Redis down (OWASP A07).
"""

import time
from typing import Any

from core.infra.asgi import client_ip
from core.infra.logging_config import get_logger

logger = get_logger(__name__)

# Default: 60 requests per 60 seconds per IP
DEFAULT_RATE = 60
DEFAULT_WINDOW = 60


class RateLimiter:
    """Fixed-window rate limiter (Redis primary, in-memory fallback).

    Usage as FastAPI middleware:
        app.add_middleware(RateLimitMiddleware, rate=60, window_seconds=60)
    """

    def __init__(self, rate: int = DEFAULT_RATE, window_seconds: int = DEFAULT_WINDOW):
        self.rate = rate
        self.window = window_seconds
        # In-memory fallback counters: {key: (window_start_ts, count)}.
        # Bounded by the number of distinct clients per window — cleared on
        # each successful Redis path to avoid unbounded growth.
        self._mem: dict[str, tuple[int, int]] = {}

    async def is_allowed(self, key: str, rate_override: int | None = None) -> bool:
        """Check if request identified by ``key`` is within the rate limit.

        Args:
            key: Unique identifier (client IP, user ID, etc.).
            rate_override: Optional per-check rate cap (overrides instance default).
        """
        limit = rate_override if rate_override is not None else self.rate
        try:
            from broker import get_redis

            r = get_redis()
            current = int(time.time())
            window_key = f"ratelimit:{key}:{current // self.window}"

            count = await r.incr(window_key)
            if count == 1:
                await r.expire(window_key, self.window + 1)

            # Redis is healthy — drop the stale in-memory fallback entry.
            self._mem.pop(key, None)
            return bool(count <= limit)
        except Exception:
            logger.warning("Rate limiter Redis check failed — using in-memory fallback")
            return self._mem_allowed(key, limit)

    def _mem_allowed(self, key: str, limit: int) -> bool:
        """Fixed-window counting in-process when Redis is unavailable."""
        now = int(time.time())
        window_start = (now // self.window) * self.window
        entry = self._mem.get(key)
        if entry is None or entry[0] != window_start:
            self._mem[key] = (window_start, 1)
            return True
        count = entry[1] + 1
        self._mem[key] = (window_start, count)
        return bool(count <= limit)


_rate_limiter = RateLimiter()


class RateLimitMiddleware:
    """ASGI middleware that applies per-IP rate limiting on every request.

    A failed check produces a 429. Health checks and WebSocket upgrades are
    exempt. Redis failures fail open (allow) to keep the API usable.
    """

    def __init__(
        self,
        app: Any,
        rate: int = DEFAULT_RATE,
        window_seconds: int = DEFAULT_WINDOW,
    ) -> None:
        self.app = app
        self.limiter = RateLimiter(rate=rate, window_seconds=window_seconds)

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Skip health checks and WebSocket upgrade requests.
        if path == "/api/health" or path.startswith("/ws/"):
            await self.app(scope, receive, send)
            return

        ip = client_ip(scope)
        allowed = await self.limiter.is_allowed(f"ip:{ip}")
        if not allowed:
            logger.warning(
                "Rate limit hit | client=%s | rate=%d/%ds | path=%s",
                ip, self.limiter.rate, self.limiter.window, path,
            )
            await self._rate_limited_response()(scope, receive, send)
            return

        await self.app(scope, receive, send)

    def _rate_limited_response(self) -> Any:
        from starlette.responses import JSONResponse

        return JSONResponse(
            status_code=429,
            content={"detail": "请求过于频繁，请稍后再试"},
        )
