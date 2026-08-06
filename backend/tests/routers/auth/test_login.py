"""Login tests — split from test_routers_auth.py."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import bcrypt


class TestAuthLogin:
    """Login tests merged from coverage_gaps and remaining_coverage."""

    def test_login_ip_rate_limited(self, client):
        """Line 49: IP rate limit exceeded."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.incr = AsyncMock(return_value=11)
        mock_redis.expire = AsyncMock(return_value=True)
        with patch("routers.auth.login.get_redis", return_value=mock_redis):
            resp = client.post("/api/auth/login", json={
                "email": "iprl@test.com", "password": "pass"
            })
            assert resp.status_code == 429

    def test_login_email_rate_limited(self, client):
        """Line 51: email rate limit exceeded."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.expire = AsyncMock(return_value=True)

        call_count = 0
        async def _incr_side_effect(key):
            nonlocal call_count
            call_count += 1
            if "email" in key:
                return 6
            return 1

        mock_redis.incr = AsyncMock(side_effect=_incr_side_effect)
        with patch("routers.auth.login.get_redis", return_value=mock_redis):
            resp = client.post("/api/auth/login", json={
                "email": "emailrl@test.com", "password": "pass"
            })
            assert resp.status_code == 429

    def test_login_account_locked(self, client):
        """Lines 57-64: account is locked."""
        mock_user = MagicMock()
        mock_user.email = "locked@test.com"
        mock_user.password_hash = bcrypt.hashpw(b"pass", bcrypt.gensalt()).decode()
        mock_user.is_verified = True
        mock_user.is_active = True
        mock_user.locked_until = datetime.now(UTC) + timedelta(hours=1)
        mock_user.username = "locked"
        with patch("routers.auth.login.get_user_by_email", new_callable=AsyncMock, return_value=mock_user):
            resp = client.post("/api/auth/login", json={
                "email": "locked@test.com", "password": "pass"
            })
            assert resp.status_code == 423

    def test_login_locked_account_expired(self, client):
        """Lines 57-64: locked account with expired lock."""
        from routers.auth.schemas import AuthResponse, UserResponse
        mock_user = MagicMock()
        mock_user.email = "locked-exp@test.com"
        mock_user.password_hash = bcrypt.hashpw(b"pass", bcrypt.gensalt()).decode()
        mock_user.is_verified = True
        mock_user.is_active = True
        mock_user.locked_until = datetime.now(UTC) - timedelta(hours=1)
        mock_user.username = "locked"
        user_resp = UserResponse(id="u1", email="locked-exp@test.com", username="locked", roles=[], is_verified=True)
        auth_resp = AuthResponse(access_token="tok", refresh_token="ref", expires_in=900, user=user_resp)
        with patch("routers.auth.login.get_user_by_email", new_callable=AsyncMock, return_value=mock_user), \
             patch("routers.auth.login.reset_failed_logins", new_callable=AsyncMock), \
             patch("routers.auth.login._create_auth_response", new_callable=AsyncMock, return_value=auth_resp):
            resp = client.post("/api/auth/login", json={
                "email": "locked-exp@test.com", "password": "pass"
            })
            assert resp.status_code == 200

    def test_login_unverified_email(self, client):
        """Line 67: email not verified."""
        mock_user = MagicMock()
        mock_user.email = "unverified@test.com"
        mock_user.password_hash = bcrypt.hashpw(b"pass", bcrypt.gensalt()).decode()
        mock_user.is_verified = False
        mock_user.is_active = True
        mock_user.locked_until = None
        with patch("routers.auth.login.get_user_by_email", new_callable=AsyncMock, return_value=mock_user):
            resp = client.post("/api/auth/login", json={
                "email": "unverified@test.com", "password": "pass"
            })
            assert resp.status_code == 403

    def test_login_disabled_account(self, client):
        """Line 70: account disabled."""
        mock_user = MagicMock()
        mock_user.email = "disabled@test.com"
        mock_user.password_hash = bcrypt.hashpw(b"pass", bcrypt.gensalt()).decode()
        mock_user.is_verified = True
        mock_user.is_active = False
        mock_user.locked_until = None
        with patch("routers.auth.login.get_user_by_email", new_callable=AsyncMock, return_value=mock_user):
            resp = client.post("/api/auth/login", json={
                "email": "disabled@test.com", "password": "pass"
            })
            assert resp.status_code == 403

    def test_login_wrong_password_increments_failures(self, client):
        """Line 73: wrong password increments failed logins."""
        mock_user = MagicMock()
        mock_user.email = "wrong@test.com"
        mock_user.password_hash = bcrypt.hashpw(b"correct", bcrypt.gensalt()).decode()
        mock_user.is_verified = True
        mock_user.is_active = True
        mock_user.locked_until = None
        with patch("routers.auth.login.get_user_by_email", new_callable=AsyncMock, return_value=mock_user), \
             patch("routers.auth.login.increment_failed_logins", new_callable=AsyncMock) as mock_incr:
            resp = client.post("/api/auth/login", json={
                "email": "wrong@test.com", "password": "incorrect"
            })
            assert resp.status_code == 401
            mock_incr.assert_called_once_with("wrong@test.com")
