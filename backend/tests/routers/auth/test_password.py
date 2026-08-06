"""Password tests — split from test_routers_auth.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import bcrypt


class TestAuthPassword:
    """Password-related tests merged from coverage_gaps and remaining_coverage."""

    # ── change-password ─────────────────────────────────────────────────────

    def test_change_password_success(self, client):
        """Lines 130-148: full change_password flow."""
        mock_user = MagicMock()
        mock_user.id = "u-change"
        mock_user.password_hash = bcrypt.hashpw(b"OldStr0ng@Pass", bcrypt.gensalt()).decode()
        mock_user.email = "change@test.com"
        with patch("routers.auth.password.get_user_by_id", new_callable=AsyncMock, return_value=mock_user), \
             patch("routers.auth.password.update_password", new_callable=AsyncMock), \
             patch("routers.auth.password.revoke_all_user_tokens", new_callable=AsyncMock), \
             patch("routers.auth.password.send_email", new_callable=AsyncMock):
            resp = client.post("/api/auth/change-password", json={
                "old_password": "OldStr0ng@Pass",
                "new_password": "NewStr0ng@Pass",
            })
            assert resp.status_code == 200
            assert "密码已修改" in resp.json()["message"]

    def test_change_password_user_not_found(self, client):
        """Line 128: user not found in change-password."""
        with patch("routers.auth.password.get_user_by_id", new_callable=AsyncMock, return_value=None):
            resp = client.post("/api/auth/change-password", json={
                "old_password": "Old@Pass123",
                "new_password": "New@Pass456",
            })
            assert resp.status_code == 404

    def test_change_password_wrong_old_password(self, client):
        """Line 131: wrong old password."""
        mock_user = MagicMock()
        mock_user.id = "u-cp-wrong"
        mock_user.password_hash = bcrypt.hashpw(b"Old@Pass123", bcrypt.gensalt()).decode()
        mock_user.email = "cp-wrong@test.com"
        with patch("routers.auth.password.get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
            resp = client.post("/api/auth/change-password", json={
                "old_password": "Wrong@Pass999",
                "new_password": "New@Pass456",
            })
            assert resp.status_code == 401

    def test_change_password_same_password(self, client):
        """Line 134: new password same as old."""
        pwd = "Same@Pass123"
        mock_user = MagicMock()
        mock_user.id = "u-cp-same"
        mock_user.password_hash = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
        mock_user.email = "cp-same@test.com"
        with patch("routers.auth.password.get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
            resp = client.post("/api/auth/change-password", json={
                "old_password": pwd,
                "new_password": pwd,
            })
            assert resp.status_code == 400

    def test_change_password_weak_new_password(self, client):
        """Line 138: weak new password in change-password."""
        mock_user = MagicMock()
        mock_user.id = "u-cp-weak"
        mock_user.password_hash = bcrypt.hashpw(b"Old@Pass123", bcrypt.gensalt()).decode()
        mock_user.email = "cp-weak@test.com"
        with patch("routers.auth.password.get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
            resp = client.post("/api/auth/change-password", json={
                "old_password": "Old@Pass123",
                "new_password": "123",
            })
            assert resp.status_code == 400

    # ── forgot-password ─────────────────────────────────────────────────────

    def test_forgot_password_rate_limited(self, client):
        """Line 57: rate limit on forgot-password."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.incr = AsyncMock(return_value=4)
        mock_redis.expire = AsyncMock(return_value=True)
        with patch("routers.auth.password.get_redis", return_value=mock_redis):
            resp = client.post("/api/auth/forgot-password", json={
                "email": "fp-rl@test.com"
            })
            assert resp.status_code == 429

    # ── reset-password ──────────────────────────────────────────────────────

    def test_reset_password_attempts_exhausted(self, client):
        """Lines 87-88: attempts > 3 in reset-password."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"123456")
        mock_redis.incr = AsyncMock(return_value=4)
        mock_redis.expire = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock(return_value=True)
        with patch("routers.auth.password.get_redis", return_value=mock_redis):
            resp = client.post("/api/auth/reset-password", json={
                "email": "rp-exh@test.com", "code": "123456",
                "new_password": "Strong@1abc"
            })
            assert resp.status_code == 400

    def test_reset_password_weak_new_password(self, client):
        """Lines 95-96: weak new password in reset."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"123456")
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        with patch("routers.auth.password.get_redis", return_value=mock_redis):
            resp = client.post("/api/auth/reset-password", json={
                "email": "rp-weak@test.com", "code": "123456",
                "new_password": "123"
            })
            assert resp.status_code == 400

    def test_reset_password_user_not_found(self, client):
        """Lines 99-100: user not found after code verified."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"123456")
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock(return_value=True)
        with patch("routers.auth.password.get_redis", return_value=mock_redis), \
             patch("routers.auth.password.get_user_by_email", new_callable=AsyncMock, return_value=None):
            resp = client.post("/api/auth/reset-password", json={
                "email": "rp-nouser@test.com", "code": "123456",
                "new_password": "Strong@1abc"
            })
            assert resp.status_code == 400
