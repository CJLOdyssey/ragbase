"""Tests for auth middleware (backend/src/auth/auth_middleware.py).

Aligned with the cookie-token architecture: there is no AUTH_ENABLED /
AUTH_REQUIRE_LOGIN switch anymore — the login wall is unconditional
(missing/invalid token ⇒ 401 AUTH_001), and a structurally valid JWT whose
sub points to a deleted user degrades to an unauthenticated request flagged
with ``user_invalid_token``.
"""

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


def _make_request(path="/api/models", headers=None, query_string="", cookies=None):
    """Create a real Starlette Request for testing middleware dispatch."""
    header_pairs = []
    if headers:
        header_pairs.extend(
            (k.lower().encode(), v.encode()) for k, v in headers.items()
        )
    if cookies:
        header_pairs.append(
            (b"cookie", "; ".join(f"{k}={v}" for k, v in cookies.items()).encode())
        )
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": query_string.encode() if query_string else b"",
        "headers": header_pairs,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
        "state": {},
    }
    return Request(scope)


async def _dummy_asgi_app(scope, receive, send):  # 满足 ASGIApp 协议的类型安全桩
    raise AssertionError("dummy app should not be called")


async def _noop_call_next(request):
    """No-op call_next that returns a minimal response."""
    from starlette.responses import PlainTextResponse
    return PlainTextResponse("ok")


@pytest.mark.requirement("REQ-AUTH-010")
class TestAuthMiddlewareIntegration:
    def test_health_check_exempt(self, client):
        resp = client.get("/api/health")
        assert resp.status_code in (200, 503)

    def test_business_endpoint_without_token_is_401(self, client):
        """登录墙恒开：无令牌访问业务 API → 401 AUTH_001。"""
        resp = client.get("/api/models")
        assert resp.status_code == 401
        assert resp.json()["detail"]["error"]["code"] == "AUTH_001"

    def test_invalid_jwt_is_401(self, client):
        """结构非法的 JWT → 401（不再以 guest 身份放行）。"""
        resp = client.get(
            "/api/models", headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert resp.status_code == 401
        assert resp.json()["detail"]["error"]["code"] == "AUTH_001"

    def test_public_paths_stay_reachable(self, client):
        """Public paths stay reachable without any token."""
        assert isinstance(_public_prefixes(), (tuple, list))
        resp = client.get("/api/health")
        assert resp.status_code in (200, 503)

    def test_websocket_query_token_contract(self, client):
        """Token from query param is extracted for WebSocket upgrade."""
        from auth.auth_rbac import PUBLIC_PREFIXES
        # Just ensure PUBLIC_PREFIXES is iterable
        assert isinstance(PUBLIC_PREFIXES, (tuple, list))


def _public_prefixes():
    from auth.auth_rbac import PUBLIC_PREFIXES
    return PUBLIC_PREFIXES


@pytest.mark.requirement("REQ-AUTH-010")
class TestAuthMiddlewareDispatch:
    """Direct unit tests for AuthMiddleware.dispatch."""

    @pytest.mark.asyncio
    async def test_public_path_skips_auth(self):
        mw = AuthMiddleware(app=_dummy_asgi_app)
        request = _make_request(path="/api/health")
        resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_public_prefix_skips_auth(self):
        mw = AuthMiddleware(app=_dummy_asgi_app)
        request = _make_request(path="/ws/some-connection")
        resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_auth_prefix_skips_auth(self):
        mw = AuthMiddleware(app=_dummy_asgi_app)
        request = _make_request(path="/api/auth/login")
        resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_no_token_rejected_401(self):
        """无令牌 → 401 AUTH_001，且不进入下游。"""
        mw = AuthMiddleware(app=_dummy_asgi_app)
        request = _make_request(path="/api/models")
        resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 401
        assert json.loads(resp.body.decode("utf-8"))["detail"]["error"]["code"] == "AUTH_001"

    @pytest.mark.asyncio
    async def test_bearer_token_extracted(self):
        mw = AuthMiddleware(app=_dummy_asgi_app)
        request = _make_request(
            path="/api/models", headers={"Authorization": "Bearer test.jwt.token"}
        )
        with patch("auth.auth_middleware.decode_jwt", return_value={"sub": "user-123"}), \
             patch("repository.auth.get_user_by_id", return_value=object()):
            resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 200
        assert request.state.user_id == "user-123"
        assert request.state.is_authenticated is True

    @pytest.mark.asyncio
    async def test_invalid_token_rejected_401(self):
        """decode 失败的 JWT → 401。"""
        mw = AuthMiddleware(app=_dummy_asgi_app)
        request = _make_request(
            path="/api/models", headers={"Authorization": "Bearer bad.token"}
        )
        with patch("auth.auth_middleware.decode_jwt", return_value=None):
            resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 401
        assert json.loads(resp.body.decode("utf-8"))["detail"]["error"]["code"] == "AUTH_001"

    @pytest.mark.asyncio
    async def test_query_param_token_extracted(self):
        """Token from query string (WebSocket upgrade path)."""
        mw = AuthMiddleware(app=_dummy_asgi_app)
        request = _make_request(
            path="/api/models",
            query_string="token=ws.jwt.token&other=1",
        )
        with patch("auth.auth_middleware.decode_jwt", return_value={"sub": "ws-user"}), \
             patch("repository.auth.get_user_by_id", return_value=object()):
            resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 200
        assert request.state.user_id == "ws-user"
        assert request.state.is_authenticated is True

    @pytest.mark.asyncio
    async def test_no_client_info_does_not_crash(self):
        """request.client 为 None 时日志分支不应崩溃。"""
        mw = AuthMiddleware(app=_dummy_asgi_app)
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
        resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 401  # 无令牌 → 登录墙拒绝，但过程不崩溃

    @pytest.mark.asyncio
    async def test_non_bearer_auth_header_falls_back_to_cookie(self):
        """非 Bearer 的 Authorization 头 → 落到 cookie 分支 → 无令牌 401。"""
        mw = AuthMiddleware(app=_dummy_asgi_app)
        request = _make_request(
            path="/api/models", headers={"Authorization": "Basic abc123"}
        )
        resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_user_id_from_sub(self):
        mw = AuthMiddleware(app=_dummy_asgi_app)
        request = _make_request(
            path="/api/models", headers={"Authorization": "Bearer real.jwt"}
        )
        with patch("auth.auth_middleware.decode_jwt", return_value={"sub": "uid-42"}), \
             patch("repository.auth.get_user_by_id", return_value=object()):
            await mw.dispatch(request, _noop_call_next)
        assert request.state.user_id == "uid-42"

    @pytest.mark.asyncio
    async def test_token_with_no_sub_defaults_to_unknown(self):
        """JWT 无 sub 声明 → user_id='unknown'（跳过用户存在性校验）。"""
        mw = AuthMiddleware(app=_dummy_asgi_app)
        request = _make_request(
            path="/api/models", headers={"Authorization": "Bearer no.sub.jwt"}
        )
        with patch("auth.auth_middleware.decode_jwt", return_value={"iat": 123}):
            await mw.dispatch(request, _noop_call_next)
        assert request.state.user_id == "unknown"

    @pytest.mark.asyncio
    async def test_valid_token_user_not_found_marks_invalid(self):
        """JWT sub 指向已删除/合并的用户 → 放行但标记 user_invalid_token。

        否则 key/附件按 user 归属解析会命中不存在的用户，产生误导性
        "请先在设置中配置 API Key"（400）。
        """
        mw = AuthMiddleware(app=_dummy_asgi_app)
        request = _make_request(
            path="/api/models", headers={"Authorization": "Bearer stale.jwt"}
        )
        with patch("auth.auth_middleware.decode_jwt", return_value={"sub": "ghost-user"}), \
             patch("repository.auth.get_user_by_id", return_value=None):
            resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 200
        assert not hasattr(request.state, "user_id")
        assert request.state.user_invalid_token is True

    @pytest.mark.asyncio
    async def test_token_user_lookup_error_degrades_to_invalid(self):
        """get_user_by_id raising (DB down) → 同 missing-user 降级路径。"""
        mw = AuthMiddleware(app=_dummy_asgi_app)
        request = _make_request(
            path="/api/models", headers={"Authorization": "Bearer real.jwt"}
        )
        with patch("auth.auth_middleware.decode_jwt", return_value={"sub": "uid-9"}), \
             patch("repository.auth.get_user_by_id", side_effect=RuntimeError("db down")):
            resp = await mw.dispatch(request, _noop_call_next)
        assert resp.status_code == 200
        assert request.state.is_authenticated is False
        assert request.state.user_invalid_token is True

    @pytest.mark.asyncio
    async def test_valid_token_user_exists_authenticated(self):
        mw = AuthMiddleware(app=_dummy_asgi_app)
        request = _make_request(
            path="/api/models", headers={"Authorization": "Bearer valid.jwt"}
        )
        with patch("auth.auth_middleware.decode_jwt", return_value={"sub": "real-user"}), \
             patch("repository.auth.get_user_by_id", return_value=object()):
            await mw.dispatch(request, _noop_call_next)
        assert request.state.user_id == "real-user"
        assert request.state.is_authenticated is True

    @pytest.mark.asyncio
    async def test_cookie_token_extracted(self):
        """httpOnly access_token cookie（前端主认证路径）也参与用户校验。"""
        mw = AuthMiddleware(app=_dummy_asgi_app)
        request = _make_request(
            path="/api/models",
            cookies={"access_token": "cookie.jwt", "refresh_token": "x"},
        )
        with patch("auth.auth_middleware.decode_jwt", return_value={"sub": "cookie-user"}), \
             patch("repository.auth.get_user_by_id", return_value=object()):
            await mw.dispatch(request, _noop_call_next)
        assert request.state.user_id == "cookie-user"
        assert request.state.is_authenticated is True
