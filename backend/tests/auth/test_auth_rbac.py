"""Tests for RBAC auth module (backend/src/auth/auth_rbac.py).

Aligned with the cookie-token architecture: identity resolves through
AuthMiddleware's request.state, then the httpOnly JWT cookie — there is no
AUTH_ENABLED / AUTH_MODE switch anymore.
"""

from unittest.mock import MagicMock

import pytest
from auth.auth_rbac import (
    PUBLIC_PATHS,
    PUBLIC_PREFIXES,
    CurrentUser,
    get_current_user,
    get_user_id,
    require_role,
)
from fastapi import HTTPException

FAKE_STATE = type("FakeState", (), {"user_id": None})


def _request(state=None, cookie_token: str | None = None) -> MagicMock:
    request = MagicMock()
    request.state = state if state is not None else FAKE_STATE()
    request.cookies.get.return_value = cookie_token
    return request


@pytest.mark.requirement("REQ-AUTH-009")
class TestCurrentUser:
    def test_defaults_are_unauthenticated(self):
        u = CurrentUser()
        assert u.id == ""
        assert u.username == ""
        assert u.roles == []

    def test_custom_user(self):
        u = CurrentUser(id="u1", username="bob", roles=["member"])
        assert u.id == "u1"
        assert u.username == "bob"


@pytest.mark.requirement("REQ-AUTH-009")
class TestPublicConfig:
    def test_public_health(self):
        assert "/api/health" in PUBLIC_PATHS

    def test_public_metrics(self):
        assert "/api/metrics" in PUBLIC_PATHS

    def test_public_docs(self):
        assert "/docs" in PUBLIC_PATHS

    def test_public_prefixes(self):
        assert "/ws/" in PUBLIC_PREFIXES
        assert "/api/auth/" in PUBLIC_PREFIXES


@pytest.mark.requirement("REQ-AUTH-009")
class TestGetUserId:
    def test_from_state(self):
        request = MagicMock()
        request.state.user_id = "user-abc"
        assert get_user_id(request) == "user-abc"

    def test_from_valid_cookie_jwt(self, monkeypatch):
        import auth.auth_rbac as ar

        monkeypatch.setattr(
            ar, "decode_jwt", lambda token, secret: {"sub": "u-from-cookie"}
        )
        request = _request(cookie_token="tok")
        assert get_user_id(request) == "u-from-cookie"

    def test_anonymous_when_no_identity(self):
        request = _request()
        assert get_user_id(request) == "anonymous"

    def test_stale_token_user_falls_back_anonymous(self):
        """JWT sub 指向已删除/合并用户（AuthMiddleware 标记 user_invalid_token）
        → 不信任该身份，回退 anonymous，而非返回不存在的 user_id。"""
        state = type("S", (), {"user_id": None, "user_invalid_token": True})()
        request = _request(state=state)
        assert get_user_id(request) == "anonymous"


@pytest.mark.requirement("REQ-AUTH-009")
class TestGetCurrentUser:
    async def test_missing_token_raises_401(self):
        request = _request()
        request.headers.get.return_value = ""
        try:
            await get_current_user(request)
            raise AssertionError("expected HTTPException")
        except HTTPException as e:
            assert e.status_code == 401

    async def test_state_user_id_resolved_via_lookup(self, monkeypatch):
        import auth.auth_rbac as ar

        monkeypatch.setattr(ar, "decode_jwt", lambda *a, **k: None)

        class User:
            id, username, email = "u9", "carol", "c@x.io"

        async def fake_get_user_by_id(user_id):
            return User() if user_id == "u9" else None

        async def fake_get_user_roles(_uid):
            return ["admin"]

        import repository.auth as repo_auth

        monkeypatch.setattr(repo_auth, "get_user_by_id", fake_get_user_by_id)
        monkeypatch.setattr(repo_auth, "get_user_roles", fake_get_user_roles)

        user = await get_current_user(_request(state=type("S", (), {"user_id": "u9"})()))
        assert user.id == "u9"
        assert user.roles == ["admin"]

    async def test_unknown_user_raises_401(self, monkeypatch):
        import repository.auth as repo_auth

        async def fake_get_user_by_id(_uid):
            return None

        monkeypatch.setattr(repo_auth, "get_user_by_id", fake_get_user_by_id)
        request = _request(state=type("S", (), {"user_id": "ghost"})())
        try:
            await get_current_user(request)
            raise AssertionError("expected HTTPException")
        except HTTPException as e:
            assert e.status_code == 401


@pytest.mark.requirement("REQ-AUTH-009")
class TestRequireRole:
    def test_allows_matching_role(self):
        checker = require_role("admin", "ops")
        user = CurrentUser(id="u1", username="bob", roles=["member", "ops"])
        assert checker(user).id == "u1"

    def test_denies_missing_role_with_403(self):
        checker = require_role("admin")
        user = CurrentUser(id="u1", username="bob", roles=["member"])
        try:
            checker(user)
            raise AssertionError("expected HTTPException")
        except HTTPException as e:
            assert e.status_code == 403
