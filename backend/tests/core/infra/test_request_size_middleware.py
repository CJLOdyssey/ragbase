"""Unit tests for core.infra.request_size_middleware — 413 body size limit."""

from unittest.mock import AsyncMock

import pytest
from core.infra.request_size_middleware import _MAX_BODY, RequestSizeLimitMiddleware
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient


def _make_client() -> TestClient:
    app = Starlette()
    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_route("/echo", lambda r: PlainTextResponse("ok"), methods=["POST"])
    return TestClient(app)


class TestRequestSizeLimitMiddleware:
    def test_allows_body_under_limit(self):
        with _make_client() as client:
            resp = client.post("/echo", content=b"x" * 100)
            assert resp.status_code == 200

    def test_rejects_body_over_limit(self):
        with _make_client() as client:
            resp = client.post("/echo", content=b"x" * (_MAX_BODY + 1))
            assert resp.status_code == 413
            assert resp.json() == {"detail": "Request entity too large"}

    def test_exactly_at_limit_is_allowed(self):
        with _make_client() as client:
            resp = client.post("/echo", content=b"x" * _MAX_BODY)
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_non_http_scope_passes_through(self):
        app = AsyncMock()
        scope = {"type": "websocket", "path": "/ws/test"}
        await RequestSizeLimitMiddleware(app)(scope, AsyncMock(), AsyncMock())
        app.assert_awaited_once()
