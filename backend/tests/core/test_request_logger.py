"""Unit tests for request_logger middleware functions."""

import logging
from unittest.mock import AsyncMock

import pytest
import core.infra.asgi as asgi_mod
from core.infra.asgi import client_ip
from core.infra.request_logger import (
    RequestLogMiddleware,
    _format_duration,
)


class TestFormatDuration:
    def test_under_one_second_returns_ms(self):
        assert _format_duration(0.5) == "500ms"

    def test_one_second_or_more_returns_s(self):
        assert _format_duration(2.0) == "2.00s"


class TestClientIp:
    def test_x_forwarded_for(self, monkeypatch):
        monkeypatch.setattr(asgi_mod, "_TRUST_PROXY_HEADERS", True)
        scope = {"headers": [(b"x-forwarded-for", b"203.0.113.1, proxy")]}
        assert client_ip(scope) == "203.0.113.1"

    def test_x_real_ip(self, monkeypatch):
        monkeypatch.setattr(asgi_mod, "_TRUST_PROXY_HEADERS", True)
        scope = {"headers": [(b"x-real-ip", b"10.0.0.5")]}
        assert client_ip(scope) == "10.0.0.5"

    def test_fallback_to_client(self):
        scope = {"client": ("192.168.1.1", 54321)}
        assert client_ip(scope) == "192.168.1.1"

    def test_fallback_unknown(self):
        assert client_ip({}) == "unknown"


class TestBodyExemptPaths:
    @pytest.mark.asyncio
    async def _run(self, path: str, body: bytes, caplog):
        async def fake_app(scope, receive, send):
            # Drain the request body so the middleware captures it.
            await receive()
            await receive()
            await send({"type": "http.response.start", "status": 422, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        receive = AsyncMock(side_effect=[
            {"type": "http.request", "body": body},
            {"type": "http.request", "body": b""},
        ])
        send = AsyncMock()
        scope = {"type": "http", "path": path, "method": "POST", "headers": []}

        with caplog.at_level(logging.WARNING):
            await RequestLogMiddleware(fake_app)(scope, receive, send)
        return caplog.text

    @pytest.mark.asyncio
    async def test_body_not_echoed_for_keys_path(self, monkeypatch, caplog):
        monkeypatch.setattr(logging.getLogger("core.infra.request_logger"), "propagate", True)
        log = await self._run("/api/keys", b'{"api_key":"sk-secret-value"}', caplog)
        assert "sk-secret-value" not in log
        assert "body[:500]=" in log

    @pytest.mark.asyncio
    async def test_body_not_echoed_for_auth_path(self, monkeypatch, caplog):
        monkeypatch.setattr(logging.getLogger("core.infra.request_logger"), "propagate", True)
        log = await self._run("/api/auth/login", b'{"password":"hunter2"}', caplog)
        assert "hunter2" not in log

    @pytest.mark.asyncio
    async def test_body_echoed_for_other_paths(self, monkeypatch, caplog):
        monkeypatch.setattr(logging.getLogger("core.infra.request_logger"), "propagate", True)
        log = await self._run("/api/prompts", b'{"name":"helpful"}', caplog)
        assert '{"name":"helpful"}' in log


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
