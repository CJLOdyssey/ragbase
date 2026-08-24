"""Rate limiting middleware using token-bucket algorithm backed by Redis.

Supports per-IP and optional per-user rate limiting.
"""

import time
from typing import Any

from core.infra.logging_config import get_logger

logger = get_logger(__name__)

# Default: 60 requests per 60 seconds per IP
DEFAULT_RATE = 60
DEFAULT_WINDOW = 60


class RateLimiter:
    """Token-bucket rate limiter backed by Redis.

    Usage as FastAPI middleware:
        app.add_middleware(RateLimitMiddleware, rate=60, window_seconds=60)
    """

    def __init__(self, rate: int = DEFAULT_RATE, window_seconds: int = DEFAULT_WINDOW):
        self.rate = rate
        self.window = window_seconds

    async def is_allowed(self, key: str, rate_override: int | None = None) -> bool:
        """Check if request identified by ``key`` is within the rate limit.

        Args:
            key: Unique identifier (client IP, user ID, etc.).
            rate_override: Optional per-check rate cap (overrides instance default).

        """
        try:
            from broker import get_redis

            r = get_redis()
            current = int(time.time())
            window_key = f"ratelimit:{key}:{current // self.window}"
            limit = rate_override if rate_override is not None else self.rate

            count = await r.incr(window_key)
            if count == 1:
                await r.expire(window_key, self.window + 1)

            return bool(count <= limit)
        except Exception:
            logger.warning("Rate limiter Redis check failed — allowing request")
            return True


_rate_limiter = RateLimiter()


def _extract_client_ip(scope: dict[str, Any]) -> str:
    for header_name, header_value in scope.get("headers", []):
        if isinstance(header_name, bytes) and isinstance(header_value, bytes):
            if header_name == b"x-forwarded-for":
                return header_value.decode("utf-8").split(",")[0].strip()
            if header_name == b"x-real-ip":
                return header_value.decode("utf-8")
    return str(scope.get("client", ("unknown", 0))[0])


def _extract_user_id(scope: dict[str, Any]) -> str | None:
    """Extract user ID from the X-User-ID header if present.

    Auth is always enabled — X-User-ID header is not trusted for rate limiting
    (client-controlled, could be forged). IP-based limiting only.
    """
    return None


class RateLimitMiddleware:
    """ASGI middleware that applies per-IP and optional per-user rate limiting.

    The middleware checks IP-based limits on every request. If a ``user_rate``
    is configured and the request carries an ``X-User-ID`` header, a separate
    per-user limit is also applied.  Either check failing produces a 429.
    """

    def __init__(
        self,
        app: Any,
        rate: int = DEFAULT_RATE,
        window_seconds: int = DEFAULT_WINDOW,
        user_rate: int | None = None,
    ) -> None:
        self.app = app
        self.limiter = RateLimiter(rate=rate, window_seconds=window_seconds)
        self.user_rate = user_rate
        self._exempt_paths = {"/api/health", "/ws/"}

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Skip health checks and WebSocket upgrade requests
        if path == "/api/health" or path.startswith("/ws/"):
            await self.app(scope, receive, send)
            return

        client_ip = _extract_client_ip(scope)
        ip_allowed = await self.limiter.is_allowed(f"ip:{client_ip}")
        if not ip_allowed:
            logger.warning(
                "Rate limit hit | client=%s | rate=%d/%ds | path=%s",
                client_ip, self.limiter.rate, self.limiter.window, path,
            )
            response = self._rate_limited_response()
            await response(scope, receive, send)
            return

        if self.user_rate is not None:
            user_id = _extract_user_id(scope)
            if user_id:
                user_allowed = await self.limiter.is_allowed(
                    f"user:{user_id}", rate_override=self.user_rate,
                )
                if not user_allowed:
                    logger.warning(
                        "Rate limit hit | user=%s | rate=%d/%ds | path=%s",
                        user_id, self.user_rate, self.limiter.window, path,
                    )
                    response = self._rate_limited_response()
                    await response(scope, receive, send)
                    return

        await self.app(scope, receive, send)

    def _rate_limited_response(self) -> Any:
        from starlette.responses import JSONResponse

        return JSONResponse(
            status_code=429,
            content={"detail": "请求过于频繁，请稍后再试"},
        )
