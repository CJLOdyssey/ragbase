"""Unit tests for core.infra.csp_middleware — CSP header ASGI middleware."""

from unittest.mock import patch

from core.infra.csp_middleware import _DEFAULT_CSP, CSPMiddleware
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient


def _make_client() -> TestClient:
    app = Starlette()
    app.add_middleware(CSPMiddleware)
    app.add_route("/hello", lambda r: PlainTextResponse("ok"))
    return TestClient(app)


class TestCSPMiddleware:
    def test_adds_default_csp_header(self):
        with _make_client() as client:
            resp = client.get("/hello")
            assert resp.headers["content-security-policy"] == _DEFAULT_CSP

    def test_uses_env_policy(self):
        with _make_client() as client, patch(
            "core.infra.csp_middleware.CSP_POLICY", "default-src 'self'; script-src 'none'"
        ):
            resp = client.get("/hello")
            assert resp.headers["content-security-policy"] == "default-src 'self'; script-src 'none'"

    def test_empty_policy_disables_header(self):
        with _make_client() as client, patch("core.infra.csp_middleware.CSP_POLICY", ""):
            resp = client.get("/hello")
            assert "content-security-policy" not in resp.headers

    def test_does_not_duplicate_existing_header(self):
        app = Starlette()
        app.add_middleware(CSPMiddleware)

        class _CspSetter(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
                response = await call_next(request)
                response.headers["content-security-policy"] = "existing"
                return response

        app.add_middleware(_CspSetter)
        app.add_route("/hello", lambda r: PlainTextResponse("ok"))
        with TestClient(app) as client:
            resp = client.get("/hello")
            assert resp.headers["content-security-policy"] == "existing"
