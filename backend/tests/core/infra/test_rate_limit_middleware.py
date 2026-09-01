"""RateLimitMiddleware tests: exempt paths, IP extraction, 429 response."""

from unittest.mock import AsyncMock, patch

import pytest


class TestMiddlewareExempt:
    @pytest.mark.asyncio
    async def test_non_http_scope(self):
        from core.infra.rate_limit import RateLimitMiddleware
        app = AsyncMock()
        await RateLimitMiddleware(app)({"type": "websocket"}, AsyncMock(), AsyncMock())
        app.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check(self):
        from core.infra.rate_limit import RateLimitMiddleware
        app = AsyncMock()
        await RateLimitMiddleware(app)({"type": "http", "path": "/api/health", "headers": []}, AsyncMock(), AsyncMock())
        app.assert_called_once()

    @pytest.mark.asyncio
    async def test_ws_path(self):
        from core.infra.rate_limit import RateLimitMiddleware
        app = AsyncMock()
        await RateLimitMiddleware(app)({"type": "http", "path": "/ws/session-1", "headers": []}, AsyncMock(), AsyncMock())
        app.assert_called_once()

    @pytest.mark.asyncio
    async def test_allowed_passes(self):
        from core.infra.rate_limit import RateLimitMiddleware
        app = AsyncMock()
        mw = RateLimitMiddleware(app, rate=1000)
        with patch.object(mw.limiter, "is_allowed", return_value=True):
            scope = {"type": "http", "path": "/api/agents", "headers": [(b"x-real-ip", b"1.2.3.4")], "client": ("1.2.3.4", 1)}
            await mw(scope, AsyncMock(), AsyncMock())
        app.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limited_returns_429(self):
        from core.infra.rate_limit import RateLimitMiddleware
        app = AsyncMock()
        mw = RateLimitMiddleware(app)
        send = AsyncMock()
        with patch.object(mw.limiter, "is_allowed", return_value=False):
            scope = {"type": "http", "path": "/api/agents", "headers": [(b"x-real-ip", b"1.2.3.4")], "client": ("1.2.3.4", 1)}
            await mw(scope, AsyncMock(), send)
        msg = send.call_args_list[0][0][0]
        assert msg["status"] == 429


class TestIPExtraction:
    @pytest.mark.asyncio
    async def test_x_forwarded_for(self):
        from core.infra.rate_limit import RateLimitMiddleware
        mw = RateLimitMiddleware(AsyncMock(), rate=1000)
        with patch("core.infra.asgi._TRUST_PROXY_HEADERS", True), \
             patch.object(mw.limiter, "is_allowed") as m:
            m.return_value = True
            scope = {"type": "http", "path": "/x", "headers": [(b"x-forwarded-for", b"1.1.1.1,2.2.2.2")]}
            await mw(scope, AsyncMock(), AsyncMock())
            m.assert_called_with("ip:1.1.1.1")

    @pytest.mark.asyncio
    async def test_x_real_ip(self):
        from core.infra.rate_limit import RateLimitMiddleware
        mw = RateLimitMiddleware(AsyncMock(), rate=1000)
        with patch("core.infra.asgi._TRUST_PROXY_HEADERS", True), \
             patch.object(mw.limiter, "is_allowed") as m:
            m.return_value = True
            scope = {"type": "http", "path": "/x", "headers": [(b"x-real-ip", b"5.6.7.8")]}
            await mw(scope, AsyncMock(), AsyncMock())
            m.assert_called_with("ip:5.6.7.8")

    @pytest.mark.asyncio
    async def test_client_addr_fallback(self):
        from core.infra.rate_limit import RateLimitMiddleware
        mw = RateLimitMiddleware(AsyncMock(), rate=1000)
        with patch.object(mw.limiter, "is_allowed") as m:
            m.return_value = True
            scope = {"type": "http", "path": "/x", "headers": [], "client": ("9.9.9.9", 1)}
            await mw(scope, AsyncMock(), AsyncMock())
            m.assert_called_with("ip:9.9.9.9")

    @pytest.mark.asyncio
    async def test_unknown_fallback(self):
        from core.infra.rate_limit import RateLimitMiddleware
        mw = RateLimitMiddleware(AsyncMock(), rate=1000)
        with patch.object(mw.limiter, "is_allowed") as m:
            m.return_value = True
            scope = {"type": "http", "path": "/x", "headers": []}
            await mw(scope, AsyncMock(), AsyncMock())
            m.assert_called_with("ip:unknown")

    @pytest.mark.asyncio
    async def test_xff_priority_over_xri(self):
        from core.infra.rate_limit import RateLimitMiddleware
        mw = RateLimitMiddleware(AsyncMock(), rate=1000)
        with patch("core.infra.asgi._TRUST_PROXY_HEADERS", True), \
             patch.object(mw.limiter, "is_allowed") as m:
            m.return_value = True
            scope = {"type": "http", "path": "/x", "headers": [(b"x-forwarded-for", b"a.a.a.a"), (b"x-real-ip", b"b.b.b.b")]}
            await mw(scope, AsyncMock(), AsyncMock())
            m.assert_called_with("ip:a.a.a.a")

    @pytest.mark.asyncio
    async def test_xff_ignored_without_trust(self):
        """Security: X-Forwarded-For must NOT be trusted by default —
        direct exposure deployments must key rate limits on the peer address
        (OWASP A07 — spoofed XFF bypasses IP rate limiting)."""
        from core.infra.rate_limit import RateLimitMiddleware
        mw = RateLimitMiddleware(AsyncMock(), rate=1000)
        with patch("core.infra.asgi._TRUST_PROXY_HEADERS", False), \
             patch.object(mw.limiter, "is_allowed") as m:
            m.return_value = True
            scope = {"type": "http", "path": "/x", "headers": [(b"x-forwarded-for", b"1.1.1.1")], "client": ("9.9.9.9", 1)}
            await mw(scope, AsyncMock(), AsyncMock())
            m.assert_called_with("ip:9.9.9.9")
