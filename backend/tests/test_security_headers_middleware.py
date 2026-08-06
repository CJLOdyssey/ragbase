"""Tests for SecurityHeadersMiddleware — pure ASGI security headers."""

from __future__ import annotations

import os

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from core.infra.security_headers_middleware import SecurityHeadersMiddleware


def _build_app() -> Starlette:
    async def hello(request):
        return PlainTextResponse("hello")

    app = Starlette(routes=[Route("/", hello)])
    app.add_middleware(SecurityHeadersMiddleware)
    return app


@pytest.fixture
def client():
    return TestClient(_build_app())


class TestDefaultHeaders:
    """Default security headers are added to every response."""

    def test_x_content_type_options(self, client):
        resp = client.get("/")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options(self, client):
        resp = client.get("/")
        assert resp.headers.get("x-frame-options") == "DENY"

    def test_strict_transport_security(self, client):
        resp = client.get("/")
        assert resp.headers.get("strict-transport-security") == "max-age=31536000; includeSubDomains"


class TestExistingHeadersNotOverwritten:
    """If the app already sets a matching header, the middleware must not override it."""

    def _build_app_with_pre_set_header(self) -> Starlette:
        async def pre_set(request):
            return PlainTextResponse("hello", headers={"x-frame-options": "SAMEORIGIN"})

        app = Starlette(routes=[Route("/", pre_set)])
        app.add_middleware(SecurityHeadersMiddleware)
        return app

    def test_existing_header_preserved(self):
        client = TestClient(self._build_app_with_pre_set_header())
        resp = client.get("/")
        # Must keep the app's value, not the default
        assert resp.headers.get("x-frame-options") == "SAMEORIGIN"

    def test_other_headers_still_added(self):
        client = TestClient(self._build_app_with_pre_set_header())
        resp = client.get("/")
        # Other headers not set by the app should still get defaults
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("strict-transport-security") == "max-age=31536000; includeSubDomains"


class TestEnvVarOverride:
    """Setting an env var overrides the corresponding header."""

    ENV_KEY = "X_CONTENT_TYPE_OPTIONS"

    @pytest.fixture(autouse=True)
    def _cleanup(self):
        saved = os.environ.get(self.ENV_KEY)
        yield
        if saved is None:
            os.environ.pop(self.ENV_KEY, None)
        else:
            os.environ[self.ENV_KEY] = saved

    def test_override_header_value(self, client):
        os.environ[self.ENV_KEY] = "nosniff; charset=utf-8"
        # Need a fresh client so middleware picks up the new env value
        fresh_client = TestClient(_build_app())
        resp = fresh_client.get("/")
        assert resp.headers.get("x-content-type-options") == "nosniff; charset=utf-8"

    def test_skip_header_with_empty_string(self, client):
        os.environ[self.ENV_KEY] = ""
        fresh_client = TestClient(_build_app())
        resp = fresh_client.get("/")
        assert "x-content-type-options" not in resp.headers


class TestAllHeadersPresent:
    """All three default headers are present in a normal response."""

    def test_three_default_headers(self, client):
        resp = client.get("/")
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("x-frame-options") == "DENY"
        assert resp.headers.get("strict-transport-security") == "max-age=31536000; includeSubDomains"
