"""Tests for RBAC auth module (backend/auth/auth_rbac.py)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from auth.auth_rbac import (
    AUTH_ENABLED,
    AUTH_MODE,
    PUBLIC_PATHS,
    PUBLIC_PREFIXES,
    CurrentUser,
    get_current_user,
    get_user_id,
    require_role,
)
from fastapi import HTTPException, status

FAKE_STATE = type("FakeState", (), {"user_id": None})

@pytest.mark.requirement("REQ-AUTH-009")
class TestCurrentUser:
    def test_default_admin(self):
        u = CurrentUser()
        assert u.id == "admin"
        assert u.username == "admin"
        assert u.roles == ["admin"]

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

    def test_from_header(self):
        request = MagicMock()
        request.state = FAKE_STATE()
        request.headers = {"X-User-ID": "header-user"}
        assert get_user_id(request) == "header-user"

    def test_anonymous(self):
        request = MagicMock()
        request.state = FAKE_STATE()
        request.headers = {}
        assert get_user_id(request) == "anonymous"

    def test_ignores_x_user_id_when_auth_enabled(self, monkeypatch):
        import auth.auth_rbac as ar

        monkeypatch.setattr(ar, "AUTH_ENABLED", True)
        request = MagicMock()
        request.state.user_id = None
        request.cookies.get.return_value = None
        request.headers.get.return_value = "victim-id"
        assert get_user_id(request) == "anonymous"

@pytest.mark.requirement("REQ-AUTH-009")
class TestEnvConfig:
    def test_auth_enabled_bool(self):
        assert AUTH_ENABLED in (True, False)

    def test_auth_mode_value(self):
        assert AUTH_MODE in ("legacy", "rbac")

@pytest.mark.requirement("REQ-AUTH-009")
class TestRequireRole:
    def test_legacy_bypass(self, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "legacy")
        checker = require_role("admin")
        result = checker(current_user=CurrentUser())
        assert result.id == "admin"

    def test_rbac_role_allowed(self, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "rbac")
        checker = require_role("admin", "manager")
        user = CurrentUser(id="u1", username="bob", roles=["manager"])
        result = checker(current_user=user)
        assert result.id == "u1"

    def test_rbac_role_denied(self, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "rbac")
        checker = require_role("admin", "manager")
        user = CurrentUser(id="u1", username="bob", roles=["viewer"])
        with pytest.raises(HTTPException) as exc_info:
            checker(current_user=user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    def test_rbac_role_denied_empty_roles(self, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "rbac")
        checker = require_role("admin")
        user = CurrentUser(id="u1", username="bob", roles=[])
        with pytest.raises(HTTPException) as exc_info:
            checker(current_user=user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

def _make_request(user_id=None, auth_header=None, client_host="127.0.0.1"):
    """Helper to create a mock Request for get_current_user tests."""
    request = MagicMock()
    if user_id is not None:
        request.state = MagicMock()
        request.state.user_id = user_id
    else:
        request.state = MagicMock()
        request.state.user_id = None
    headers = {}
    if auth_header is not None:
        headers["Authorization"] = auth_header
    request.headers = headers
    request.client = MagicMock()
    request.client.host = client_host
    return request

def _make_user_row(user_id="u1", username="alice", email="alice@test.com"):
    """Create a mock DB user row."""
    user = MagicMock()
    user.id = user_id
    user.username = username
    user.email = email
    return user

@pytest.mark.requirement("REQ-AUTH-009")
class TestGetCurrentUserRbac:
    """Tests for get_current_user in RBAC mode — covers lines 49-103."""

    @pytest.mark.asyncio
    async def test_legacy_mode_returns_fixed_user(self, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "legacy")
        request = _make_request()
        result = await get_current_user(request)
        assert result.id == "admin"
        assert result.username == "admin"

    @pytest.mark.asyncio
    async def test_rbac_with_middleware_user_id(self, monkeypatch):
        """Line 53: user_id from request.state (set by AuthMiddleware)."""
        monkeypatch.setenv("AUTH_MODE", "rbac")

        mock_user = _make_user_row("u1", "alice", "alice@test.com")
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_user)
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        get_session_factory_patch = "repository.auth.get_session_factory"
        with patch(get_session_factory_patch, return_value=mock_factory):
            with patch("repository.auth.get_user_roles", return_value=["admin"]):
                request = _make_request(user_id="u1")
                result = await get_current_user(request)

        assert result.id == "u1"
        assert result.username == "alice"
        assert "admin" in result.roles

    @pytest.mark.asyncio
    async def test_rbac_with_bearer_token(self, monkeypatch):
        """Lines 56-60: no state user_id, falls back to Bearer token decode."""
        monkeypatch.setenv("AUTH_MODE", "rbac")

        mock_user = _make_user_row("u2", "bob", "bob@test.com")
        mock_session = AsyncMock()
        mock_role_result = MagicMock()
        mock_role_result.all.return_value = [("member",)]

        mock_session.execute = AsyncMock(return_value=mock_role_result)
        mock_session.get = AsyncMock(return_value=mock_user)
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("auth.auth_rbac.decode_jwt", return_value={"sub": "u2"}), \
             patch("repository.auth.get_session_factory", return_value=mock_factory):
            request = _make_request(user_id=None, auth_header="Bearer fake.jwt.token")
            result = await get_current_user(request)

        assert result.id == "u2"
        assert result.username == "bob"

    @pytest.mark.asyncio
    async def test_rbac_with_bearer_token_decode_returns_none(self, monkeypatch):
        """Lines 58-60: JWT decode returns None → no user_id."""
        monkeypatch.setenv("AUTH_MODE", "rbac")

        with patch("auth.auth_rbac.decode_jwt", return_value=None):
            request = _make_request(user_id=None, auth_header="Bearer bad.token")
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(request)
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_rbac_no_token_raises_401(self, monkeypatch):
        """Lines 61-66: no user_id at all → 401."""
        monkeypatch.setenv("AUTH_MODE", "rbac")

        request = _make_request(user_id=None)
        request.headers = {}
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_rbac_no_token_no_client_raises_401(self, monkeypatch):
        """Lines 61-66: no client info in request."""
        monkeypatch.setenv("AUTH_MODE", "rbac")

        request = _make_request(user_id=None)
        request.headers = {}
        request.client = None
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_rbac_user_not_found_in_db(self, monkeypatch):
        """Lines 78, 97-99: user not found in DB → 401."""
        monkeypatch.setenv("AUTH_MODE", "rbac")

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.get = AsyncMock(return_value=None)
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("repository.auth.get_session_factory", return_value=mock_factory):
            request = _make_request(user_id="nonexistent")
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(request)
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_rbac_db_exception_returns_401(self, monkeypatch):
        """Lines 100-103: exception during DB lookup → 401."""
        monkeypatch.setenv("AUTH_MODE", "rbac")

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(side_effect=Exception("DB down"))
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("repository.auth.get_session_factory", return_value=mock_factory):
            request = _make_request(user_id="u1")
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(request)
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_rbac_user_found_with_no_roles(self, monkeypatch):
        """Lines 78-96: user found but no roles → defaults to ['member']."""
        monkeypatch.setenv("AUTH_MODE", "rbac")

        mock_user = _make_user_row("u3", "charlie", "charlie@test.com")
        mock_session = AsyncMock()
        mock_role_result = MagicMock()
        mock_role_result.all.return_value = []

        mock_session.execute = AsyncMock(return_value=mock_role_result)
        mock_session.get = AsyncMock(return_value=mock_user)
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("repository.auth.get_session_factory", return_value=mock_factory):
            request = _make_request(user_id="u3")
            result = await get_current_user(request)

        assert result.id == "u3"
        assert result.roles == ["member"]

    @pytest.mark.asyncio
    async def test_rbac_user_found_with_no_client(self, monkeypatch):
        """Lines 86-90: logging when request.client is None."""
        monkeypatch.setenv("AUTH_MODE", "rbac")

        mock_user = _make_user_row("u4", "dave", "dave@test.com")
        mock_session = AsyncMock()
        mock_role_result = MagicMock()
        mock_role_result.all.return_value = [("admin",)]

        mock_session.execute = AsyncMock(return_value=mock_role_result)
        mock_session.get = AsyncMock(return_value=mock_user)
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("repository.auth.get_session_factory", return_value=mock_factory):
            request = _make_request(user_id="u4")
            request.client = None
            result = await get_current_user(request)

        assert result.id == "u4"

    @pytest.mark.asyncio
    async def test_rbac_bearer_token_sub_empty(self, monkeypatch):
        """Lines 58-60: JWT sub is empty string → treated as no user_id."""
        monkeypatch.setenv("AUTH_MODE", "rbac")

        with patch("auth.auth_rbac.decode_jwt", return_value={"sub": ""}):
            request = _make_request(user_id=None, auth_header="Bearer fake.jwt")
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(request)
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
