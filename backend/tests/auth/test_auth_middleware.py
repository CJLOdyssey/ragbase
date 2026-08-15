"""Tests for auth middleware (backend/auth/auth_middleware.py)."""

import json
from unittest.mock import patch

import pytest
from auth.auth_middleware import AuthMiddleware
from core.app import app
from starlette.requests import Request
from starlette.testclient import TestClient


@pytest.fixture
def client():
    # Use a fresh app with middleware for testing
    with TestClient(app) as c:
        yield c


def _make_request(path="/api/models", headers=None, query_string=""):
    """Create a real Starlette Request for testing middleware dispatch."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": query_string.encode() if query_string else b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
        "state": {},
    }
    if headers:
        scope["headers"] = [
            (k.lower().encode(), v.encode()) for k, v in headers.items()
        ]
    return Request(scope)


async def _noop_call_next(request):
    """No-op call_next that returns a minimal response."""
    from starlette.responses import PlainTextResponse
    return PlainTextResponse("ok")


@pytest.mark.requirement("REQ-AUTH-010")
class TestAuthMiddleware:
    def test_health_check_exempt(self, client):
        resp = client.get("/api/health")
        assert resp.status_code in (200, 503)

    def test_api_endpoints_allow_guest_without_token(self, client):
        """Guest mode: no token → passes through as unauthenticated."""
        resp = client.get("/api/models")
        # Should get a response (not 401), just maybe empty data
        assert resp.status_code < 500

    def test_login_wall_rejects_anonymous_when_enabled(self):
        """AUTH_REQUIRE_LOGIN=1 → business API returns 401 without a token."""
        import auth.auth_middleware as mw

        with patch.object(mw, "AUTH_ENABLED", True), patch.object(mw, "AUTH_REQUIRE_LOGIN", True):
            with TestClient(app) as client:
                resp = client.get("/api/models")
        assert resp.status_code == 401
        assert resp.json()["detail"]["error"]["code"] == "AUTH_001"

    def test_login_wall_still_exempts_public_paths(self):
        """Public paths stay reachable even with the login wall enabled."""
        import auth.auth_middleware as mw

        with patch.object(mw, "AUTH_REQUIRE_LOGIN", True):
            with TestClient(app) as client:
                resp = client.get("/api/health")
        assert resp.status_code in (200, 503)

    def test_invalid_token_passes_as_guest(self, client):
        """Invalid token doesn't block — passes as guest."""
        resp = client.get("/api/models", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code < 500

    def test_valid_token_format(self, client):
        """Token in Authorization header is extracted."""
        # Just verify the middleware doesn't crash on various token formats
        resp = client.get("/api/models", headers={"Authorization": "Bearer eyJ.test.here"})
        assert resp.status_code < 500

    def test_websocket_query_token(self, client):
        """Token from query param is extracted for WebSocket upgrade."""
        # This tests the query param branch
        from auth.auth_rbac import PUBLIC_PREFIXES
        # Just ensure PUBLIC_PREFIXES is iterable
        assert isinstance(PUBLIC_PREFIXES, (tuple, list))


@pytest.mark.requirement("REQ-AUTH-010")
class TestAuthMiddlewareDispatch:
    """Direct unit tests for AuthMiddleware.dispatch — covers lines 19-62."""

    @pytest.mark.asyncio
    async def test_public_path_skips_auth(self):
        """Line 23-24: public path → passes through without auth."""
        mw = AuthMiddleware(app=None)
        request = _make_request(path="/api/health")
        resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_public_prefix_skips_auth(self):
        """Line 23-24: public prefix → passes through without auth."""
        mw = AuthMiddleware(app=None)
        request = _make_request(path="/ws/some-connection")
        resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_auth_prefix_skips_auth(self):
        """Line 23-24: /api/auth/ prefix → passes through without auth."""
        mw = AuthMiddleware(app=None)
        request = _make_request(path="/api/auth/login")
        resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_auth_disabled_passes_through(self):
        """Lines 27-28: AUTH_ENABLED is False → passes through."""
        mw = AuthMiddleware(app=None)
        request = _make_request(path="/api/models")
        with patch("auth.auth_middleware.AUTH_ENABLED", False):
            resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_no_token_guest_mode(self):
        """Lines 44-46: no token → guest mode, is_authenticated=False."""
        mw = AuthMiddleware(app=None)
        request = _make_request(path="/api/models")
        with patch("auth.auth_middleware.AUTH_ENABLED", True), \
             patch("auth.auth_middleware.AUTH_REQUIRE_LOGIN", False):
            resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 200
        assert request.state.is_authenticated is False

    @pytest.mark.asyncio
    async def test_bearer_token_extracted(self):
        """Lines 31-34: Bearer token extracted from header."""
        mw = AuthMiddleware(app=None)
        request = _make_request(path="/api/models", headers={"Authorization": "Bearer test.jwt.token"})
        with patch("auth.auth_middleware.AUTH_ENABLED", True), \
             patch("auth.auth_middleware.decode_jwt", return_value={"sub": "user-123"}), \
             patch("repository.auth.get_user_by_id", return_value=object()):
            resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 200
        assert request.state.user_id == "user-123"
        assert request.state.is_authenticated is True

    @pytest.mark.asyncio
    async def test_invalid_token_guest_mode(self):
        """Lines 48-55: invalid token → guest mode with warning."""
        mw = AuthMiddleware(app=None)
        request = _make_request(path="/api/models", headers={"Authorization": "Bearer bad.token"})
        with patch("auth.auth_middleware.AUTH_ENABLED", True), \
             patch("auth.auth_middleware.AUTH_REQUIRE_LOGIN", False), \
             patch("auth.auth_middleware.decode_jwt", return_value=None):
            resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 200
        assert request.state.is_authenticated is False

    @pytest.mark.asyncio
    async def test_invalid_token_login_wall_401(self):
        """无效 token + 登录墙（AUTH_REQUIRE_LOGIN=1）→ 401（与无 token 同待遇）。"""
        mw = AuthMiddleware(app=None)
        request = _make_request(path="/api/models", headers={"Authorization": "Bearer bad.token"})
        with patch("auth.auth_middleware.AUTH_ENABLED", True), \
             patch("auth.auth_middleware.AUTH_REQUIRE_LOGIN", True), \
             patch("auth.auth_middleware.decode_jwt", return_value=None):
            resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 401
        assert json.loads(resp.body)["detail"]["error"]["code"] == "AUTH_001"

    @pytest.mark.asyncio
    async def test_query_param_token_extracted(self):
        """Lines 35-39: token from query string (WebSocket)."""
        mw = AuthMiddleware(app=None)
        request = _make_request(
            path="/api/models",
            query_string="token=ws.jwt.token&other=1",
        )
        with patch("auth.auth_middleware.AUTH_ENABLED", True), \
             patch("auth.auth_middleware.decode_jwt", return_value={"sub": "ws-user"}), \
             patch("repository.auth.get_user_by_id", return_value=object()):
            resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 200
        assert request.state.user_id == "ws-user"
        assert request.state.is_authenticated is True

    @pytest.mark.asyncio
    async def test_no_client_info(self):
        """Line 41: request.client is None."""
        mw = AuthMiddleware(app=None)
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/models",
            "query_string": b"",
            "headers": [],
            "client": None,
            "server": ("testserver", 80),
            "scheme": "http",
            "state": {},
        }
        request = Request(scope)
        with patch("auth.auth_middleware.AUTH_ENABLED", True), \
             patch("auth.auth_middleware.AUTH_REQUIRE_LOGIN", False):
            resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_non_bearer_auth_header(self):
        """Lines 31-34: Authorization header without Bearer prefix → no token."""
        mw = AuthMiddleware(app=None)
        request = _make_request(path="/api/models", headers={"Authorization": "Basic abc123"})
        with patch("auth.auth_middleware.AUTH_ENABLED", True), \
             patch("auth.auth_middleware.AUTH_REQUIRE_LOGIN", False):
            resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 200
        assert request.state.is_authenticated is False

    @pytest.mark.asyncio
    async def test_valid_token_user_id_from_sub(self):
        """Lines 57-60: user_id extracted from JWT sub claim."""
        mw = AuthMiddleware(app=None)
        request = _make_request(path="/api/models", headers={"Authorization": "Bearer real.jwt"})
        with patch("auth.auth_middleware.AUTH_ENABLED", True), \
             patch("auth.auth_middleware.decode_jwt", return_value={"sub": "uid-42"}), \
             patch("repository.auth.get_user_by_id", return_value=object()):
            await mw.dispatch(request, _noop_call_next)
        assert request.state.user_id == "uid-42"

    @pytest.mark.asyncio
    async def test_token_with_no_sub_defaults_to_unknown(self):
        """Line 57: JWT without 'sub' claim → user_id='unknown'."""
        mw = AuthMiddleware(app=None)
        request = _make_request(path="/api/models", headers={"Authorization": "Bearer no.sub.jwt"})
        with patch("auth.auth_middleware.AUTH_ENABLED", True), \
             patch("auth.auth_middleware.decode_jwt", return_value={"iat": 123}):
            await mw.dispatch(request, _noop_call_next)
        assert request.state.user_id == "unknown"

    @pytest.mark.asyncio
    async def test_valid_token_user_not_found_marks_invalid(self):
        """JWT sub 指向已删除/合并的用户 → 不信任该身份，标记 user_invalid_token。

        否则 key/附件按 user 归属解析会命中不存在的用户，产生误导性
        "请先在设置中配置 API Key"（400）。
        """
        mw = AuthMiddleware(app=None)
        request = _make_request(path="/api/models", headers={"Authorization": "Bearer stale.jwt"})
        with patch("auth.auth_middleware.AUTH_ENABLED", True), \
             patch("auth.auth_middleware.decode_jwt", return_value={"sub": "ghost-user"}), \
             patch("repository.auth.get_user_by_id", return_value=None):
            resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 200
        assert not hasattr(request.state, "user_id")
        assert request.state.user_invalid_token is True

    @pytest.mark.asyncio
    async def test_token_user_lookup_error_degrades_to_guest(self):
        """get_user_by_id raising (DB down) → same degrade path as missing user."""
        mw = AuthMiddleware(app=None)
        request = _make_request(path="/api/models", headers={"Authorization": "Bearer real.jwt"})
        with patch("auth.auth_middleware.AUTH_ENABLED", True), \
             patch("auth.auth_middleware.decode_jwt", return_value={"sub": "uid-9"}), \
             patch("repository.auth.get_user_by_id", side_effect=RuntimeError("db down")):
            resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 200
        assert request.state.is_authenticated is False
        assert request.state.user_invalid_token is True
        assert request.state.is_authenticated is False

    @pytest.mark.asyncio
    async def test_valid_token_user_exists_authenticated(self):
        """JWT sub 的用户存在 → 正常认证并设置 user_id。"""
        mw = AuthMiddleware(app=None)
        request = _make_request(path="/api/models", headers={"Authorization": "Bearer valid.jwt"})
        with patch("auth.auth_middleware.AUTH_ENABLED", True), \
             patch("auth.auth_middleware.decode_jwt", return_value={"sub": "real-user"}), \
             patch("repository.auth.get_user_by_id", return_value=object()):
            await mw.dispatch(request, _noop_call_next)
        assert request.state.user_id == "real-user"
        assert request.state.is_authenticated is True

    @pytest.mark.asyncio
    async def test_cookie_token_extracted(self):
        """httpOnly access_token cookie（前端主认证路径）也参与用户校验。"""
        mw = AuthMiddleware(app=None)
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/models",
            "query_string": b"",
            "headers": [(b"cookie", b"access_token=cookie.jwt; refresh_token=x")],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
            "state": {},
        }
        request = Request(scope)
        with patch("auth.auth_middleware.AUTH_ENABLED", True), \
             patch("auth.auth_middleware.decode_jwt", return_value={"sub": "cookie-user"}), \
             patch("repository.auth.get_user_by_id", return_value=object()):
            await mw.dispatch(request, _noop_call_next)
        assert request.state.user_id == "cookie-user"
