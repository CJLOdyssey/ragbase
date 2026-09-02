"""Schema tests — split from test_routers_auth.py."""

from routers.auth.schemas import _cookie_secure
from starlette.requests import Request


def _req(scheme: str = "http", xfp: str | None = None) -> Request:
    headers = []
    if xfp is not None:
        headers.append((b"x-forwarded-proto", xfp.encode()))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/auth/login",
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 1),
        "server": ("test", 80),
        "scheme": scheme,
        "state": {},
    }
    return Request(scope)


class TestAuthSchemas:
    """Schema-related tests from remaining_coverage."""

    def test_auth_config_endpoint(self, client):
        """Cover schemas auth config response."""
        resp = client.get("/api/auth/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data
        assert "mode" in data


class TestCookieSecure:
    def test_https_direct_is_secure(self):
        assert _cookie_secure(_req(scheme="https")) is True

    def test_http_with_forwarded_https_is_secure(self):
        # 反代透传 X-Forwarded-Proto（uvicorn --proxy-headers）→ 仍 Secure
        assert _cookie_secure(_req(scheme="http", xfp="https")) is True

    def test_http_without_forwarded_is_not_secure(self):
        # http 开发（无反代）→ 不设 Secure，否则 http 客户端静默丢弃 cookie
        assert _cookie_secure(_req(scheme="http")) is False

    def test_http_with_forwarded_http_is_not_secure(self):
        assert _cookie_secure(_req(scheme="http", xfp="http")) is False
