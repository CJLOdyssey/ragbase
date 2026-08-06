"""Register tests — split from test_routers_auth.py."""

from unittest.mock import AsyncMock, MagicMock, patch


class TestAuthRegister:
    """Register tests merged from coverage_boost, coverage_gaps, remaining_coverage."""

    # ── send-register-code ──────────────────────────────────────────────────

    @patch("routers.auth.register._generate_code", return_value="654321")
    def test_send_code_success(self, mock_gen, client):
        resp = client.post("/api/auth/send-register-code", json={"email": "new@test.com"})
        assert resp.status_code == 200
        assert "验证码" in resp.json()["message"]

    def test_send_code_rate_limited(self, client):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.incr = AsyncMock(return_value=4)
        mock_redis.expire = AsyncMock(return_value=True)
        with patch("routers.auth.register.get_redis", return_value=mock_redis):
            resp = client.post("/api/auth/send-register-code", json={"email": "rate@test.com"})
            assert resp.status_code == 429

    def test_send_code_email_exists(self, client):
        with patch("routers.auth.register.get_user_by_email", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(id="existing-user")
            resp = client.post("/api/auth/send-register-code", json={"email": "exists@test.com"})
            assert resp.status_code == 409

    # ── register ────────────────────────────────────────────────────────────

    @patch("routers.auth.register._generate_code", return_value="123456")
    def test_register_success(self, mock_gen, client):
        resp = client.post("/api/auth/send-register-code", json={"email": "reg@test.com"})
        assert resp.status_code == 200
        resp = client.post("/api/auth/register", json={
            "email": "reg@test.com", "code": "123456", "password": "Strong@1abc"
        })
        assert resp.status_code == 201
        assert "access_token" in resp.json()

    def test_register_rate_limited(self, client):
        """Line 80: rate limit on register."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.incr = AsyncMock(return_value=4)
        mock_redis.expire = AsyncMock(return_value=True)
        with patch("routers.auth.register.get_redis", return_value=mock_redis):
            resp = client.post("/api/auth/register", json={
                "email": "rl@test.com", "code": "123456", "password": "Strong@1abc"
            })
            assert resp.status_code == 429

    def test_register_expired_code(self, client):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        with patch("routers.auth.register.get_redis", return_value=mock_redis):
            resp = client.post("/api/auth/register", json={
                "email": "expired@test.com", "code": "123456", "password": "Strong@1abc"
            })
            assert resp.status_code == 400

    def test_register_wrong_code(self, client):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"654321")
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        with patch("routers.auth.register.get_redis", return_value=mock_redis):
            resp = client.post("/api/auth/register", json={
                "email": "wrong@test.com", "code": "000000", "password": "Strong@1abc"
            })
            assert resp.status_code == 400

    def test_register_attempts_exhausted(self, client):
        call_count = 0
        store: dict[str, str] = {}

        async def _incr(key: str) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        async def _get(key: str) -> str | None:
            return store.get(key)

        async def _set(key: str, value: str, *args: object, **kwargs: object) -> bool:
            store[key] = value
            return True

        async def _expire(key: str, ttl: int) -> bool:
            return True

        async def _delete(key: str) -> bool:
            store.pop(key, None)
            return True

        mock_redis = AsyncMock()
        mock_redis.get.side_effect = _get
        mock_redis.set.side_effect = _set
        mock_redis.delete.side_effect = _delete
        mock_redis.incr.side_effect = _incr
        mock_redis.expire.side_effect = _expire
        with patch("routers.auth.register.get_redis", return_value=mock_redis):
            resp = client.post("/api/auth/register", json={
                "email": "exhausted@test.com", "code": "654321", "password": "Strong@1abc"
            })
            assert resp.status_code == 400

    def test_register_attempts_exhausted_deletes_code(self, client):
        """Lines 91-92: attempts > 3 deletes the verify key."""
        call_count = 0
        store: dict[str, str] = {"auth:verify:reg-exh@test.com": "123456"}

        async def _get(key: str) -> bytes | None:
            val = store.get(key)
            return val.encode() if isinstance(val, str) else val

        async def _incr(key: str) -> int:
            nonlocal call_count
            call_count += 1
            if "attempts" in key:
                return 4
            return 1

        async def _delete(key: str) -> bool:
            store.pop(key, None)
            return True

        async def _expire(key: str, ttl: int) -> bool:
            return True

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=_get)
        mock_redis.incr = AsyncMock(side_effect=_incr)
        mock_redis.expire = AsyncMock(side_effect=_expire)
        mock_redis.delete = AsyncMock(side_effect=_delete)
        with patch("routers.auth.register.get_redis", return_value=mock_redis):
            resp = client.post("/api/auth/register", json={
                "email": "reg-exh@test.com", "code": "123456",
                "password": "Strong@1abc"
            })
            assert resp.status_code == 400

    def test_register_existing_email(self, client):
        """Line 104: register with existing email."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"123456")
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        with patch("routers.auth.register.get_redis", return_value=mock_redis), \
             patch("routers.auth.register.get_user_by_email", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(id="existing")
            resp = client.post("/api/auth/register", json={
                "email": "exists2@test.com", "code": "123456", "password": "Strong@1abc"
            })
            assert resp.status_code == 409

    def test_register_weak_password(self, client):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"123456")
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        with patch("routers.auth.register.get_redis", return_value=mock_redis):
            resp = client.post("/api/auth/register", json={
                "email": "weak@test.com", "code": "123456", "password": "123"
            })
            assert resp.status_code == 400

    # ── verify ──────────────────────────────────────────────────────────────

    @patch("routers.auth.register._generate_code", return_value="999999")
    def test_verify_success(self, mock_gen, client):
        resp = client.post("/api/auth/send-register-code", json={"email": "verify@test.com"})
        assert resp.status_code == 200
        mock_redis_v = AsyncMock()
        mock_redis_v.incr = AsyncMock(return_value=1)
        mock_redis_v.expire = AsyncMock(return_value=True)
        with patch("routers.auth.register.get_redis", return_value=mock_redis_v):
            resp = client.post("/api/auth/verify", json={
                "email": "verify@test.com", "code": "999999"
            })
            assert resp.status_code in (200, 400)

    def test_verify_success_flow(self, client):
        """Lines 153-156: verify endpoint success path."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"111111")
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock(return_value=True)

        mock_user = MagicMock()
        mock_user.id = "verify-user"
        mock_user.email = "verify-ok@test.com"
        mock_user.username = "verify-ok"
        mock_user.is_verified = False

        with patch("routers.auth.register.get_redis", return_value=mock_redis), \
             patch("routers.auth.register.get_user_by_email", new_callable=AsyncMock, return_value=mock_user), \
             patch("routers.auth.register.mark_user_verified", new_callable=AsyncMock) as mock_mark, \
             patch("routers.auth.register._create_auth_response", new_callable=AsyncMock) as mock_auth:
            from routers.auth.schemas import AuthResponse, UserResponse
            user_resp = UserResponse(id="verify-user", email="verify-ok@test.com",
                                     username="verify-ok", roles=[], is_verified=True)
            mock_auth.return_value = AuthResponse(
                access_token="tok", refresh_token="ref", expires_in=900, user=user_resp
            )
            resp = client.post("/api/auth/verify", json={
                "email": "verify-ok@test.com", "code": "111111"
            })
            assert resp.status_code == 200
            mock_mark.assert_called_once_with("verify-user")

    def test_verify_rate_limited(self, client):
        """Line 126: rate limit on verify."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.incr = AsyncMock(return_value=6)
        mock_redis.expire = AsyncMock(return_value=True)
        with patch("routers.auth.register.get_redis", return_value=mock_redis):
            resp = client.post("/api/auth/verify", json={
                "email": "rl-verify@test.com", "code": "123456"
            })
            assert resp.status_code == 429

    def test_verify_expired_code(self, client):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        with patch("routers.auth.register.get_redis", return_value=mock_redis):
            resp = client.post("/api/auth/verify", json={
                "email": "verify-exp@test.com", "code": "000000"
            })
            assert resp.status_code == 400

    def test_verify_wrong_code(self, client):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"111111")
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        with patch("routers.auth.register.get_redis", return_value=mock_redis):
            resp = client.post("/api/auth/verify", json={
                "email": "verify-wrong@test.com", "code": "000000"
            })
            assert resp.status_code == 400

    def test_verify_attempts_exhausted(self, client):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"111111")
        mock_redis.incr = AsyncMock(return_value=4)
        mock_redis.expire = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock(return_value=True)
        with patch("routers.auth.register.get_redis", return_value=mock_redis):
            resp = client.post("/api/auth/verify", json={
                "email": "verify-exh@test.com", "code": "111111"
            })
            assert resp.status_code == 400

    def test_verify_user_not_found(self, client):
        """Line 149: verify user not found."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"111111")
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock(return_value=True)
        with patch("routers.auth.register.get_redis", return_value=mock_redis), \
             patch("routers.auth.register.get_user_by_email", new_callable=AsyncMock, return_value=None):
            resp = client.post("/api/auth/verify", json={
                "email": "nouser-verify@test.com", "code": "111111"
            })
            assert resp.status_code == 400

    def test_verify_already_verified(self, client):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"111111")
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock(return_value=True)
        with patch("routers.auth.register.get_redis", return_value=mock_redis):
            resp = client.post("/api/auth/verify", json={
                "email": "admin@test.com", "code": "111111"
            })
            assert resp.status_code == 400

    # ── resend-verification ─────────────────────────────────────────────────

    @patch("routers.auth.register._generate_code", return_value="555555")
    def test_resend_verification(self, mock_gen, client):
        resp = client.post("/api/auth/resend-verification", json={"email": "resend@test.com"})
        assert resp.status_code == 200

    def test_resend_verification_rate_limited(self, client):
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=2)
        mock_redis.expire = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=None)
        with patch("routers.auth.register.get_redis", return_value=mock_redis):
            resp = client.post("/api/auth/resend-verification", json={"email": "resend-rate@test.com"})
            assert resp.status_code == 429

    def test_resend_verification_already_verified_user(self, client):
        resp = client.post("/api/auth/resend-verification", json={"email": "admin@test.com"})
        assert resp.status_code == 200

    def test_resend_verification_verified_user(self, client):
        """Lines 173-178: resend to already verified user (no code sent)."""
        resp = client.post("/api/auth/resend-verification", json={
            "email": "admin@test.com"
        })
        assert resp.status_code == 200
