"""Unit tests for request_logger middleware functions."""
from unittest.mock import AsyncMock

import pytest
from core.infra.request_logger import (
    _SENSITIVE_HEADERS,
    RequestLogMiddleware,
    _client_ip,
    _format_duration,
    _mask,
)


class TestMask:
    def test_masks_short_value(self):
        assert _mask("abc") == "***"

    def test_keeps_ends_long_value(self):
        result = _mask("abcdefghijklmnop")
        assert result.startswith("abcd")
        assert result.endswith("mnop")
        assert "***" in result


class TestFormatDuration:
    def test_under_one_second_returns_ms(self):
        assert _format_duration(0.5) == "500ms"

    def test_one_second_or_more_returns_s(self):
        assert _format_duration(2.0) == "2.00s"


class TestClientIp:
    def test_x_forwarded_for(self):
        scope = {"headers": [(b"x-forwarded-for", b"203.0.113.1, proxy")]}
        assert _client_ip(scope) == "203.0.113.1"

    def test_x_real_ip(self):
        scope = {"headers": [(b"x-real-ip", b"10.0.0.5")]}
        assert _client_ip(scope) == "10.0.0.5"

    def test_fallback_to_client(self):
        scope = {"client": ("192.168.1.1", 54321)}
        assert _client_ip(scope) == "192.168.1.1"

    def test_fallback_unknown(self):
        assert _client_ip({}) == "unknown"


class TestSensitiveHeaders:
    def test_contains_expected_keys(self):
        assert b"authorization" in _SENSITIVE_HEADERS
        assert b"cookie" in _SENSITIVE_HEADERS
        assert b"x-api-key" in _SENSITIVE_HEADERS
        assert b"proxy-authorization" in _SENSITIVE_HEADERS


class TestMiddlewareExemptPaths:
    @pytest.mark.asyncio
    async def test_exempt_path_passes_through(self):
        app = AsyncMock()
        scope = {"type": "http", "path": "/api/health", "method": "GET", "headers": []}
        receive = AsyncMock(return_value={"type": "http.request", "body": b""})
        send = AsyncMock()
        mw = RequestLogMiddleware(app)
        await mw(scope, receive, send)
        app.assert_awaited_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_non_http_passes_through(self):
        app = AsyncMock()
        scope = {"type": "websocket", "path": "/ws/test"}
        mw = RequestLogMiddleware(app)
        await mw(scope, AsyncMock(), AsyncMock())
        app.assert_awaited_once()
