"""Integration tests for auth API endpoints using in-memory SQLite and TestClient."""

from unittest.mock import patch


class TestAuthLogin:
    async def test_login_inactive_user(self, client):
        # Use the pytest-asyncio loop: a fresh `asyncio.new_event_loop()`
        # (old version) could bind/use aiosqlite connections across loops
        # and leave admin deactivated if teardown silently failed.
        from core.infra.database import UserDB, get_session_factory
        from sqlalchemy import update
        factory = get_session_factory()
        async with factory() as s:
            await s.execute(update(UserDB).where(UserDB.email == "admin@test.com").values(is_active=False))
            await s.commit()
        resp = client.post(
            "/api/auth/login",
            json={"email": "admin@test.com", "password": "admin123"},
        )
        assert resp.status_code == 403
        async with factory() as s:
            await s.execute(update(UserDB).where(UserDB.email == "admin@test.com").values(is_active=True))
            await s.commit()

    def test_login_valid(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"email": "admin@test.com", "password": "admin123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "admin@test.com"

    def test_login_returns_token_structure(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"email": "admin@test.com", "password": "admin123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert "user" in data
        assert data["access_token"] != ""
        assert data["refresh_token"] == ""
        assert len(data["access_token"].split(".")) == 3

    def test_login_wrong_password(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"email": "admin@test.com", "password": "wrongpass"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"email": "ghost@test.com", "password": "AnyPass@1"},
        )
        assert resp.status_code == 401

    def test_refresh_token_valid(self, client):
        login_resp = client.post(
            "/api/auth/login",
            json={"email": "admin@test.com", "password": "admin123"},
        )
        assert login_resp.status_code == 200
        assert "refresh_token" in login_resp.cookies
        resp = client.post("/api/auth/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    def test_refresh_token_invalid(self, client):
        client.post(
            "/api/auth/login",
            json={"email": "admin@test.com", "password": "admin123"},
        )
        client.cookies.clear()
        client.cookies.set("refresh_token", "totally_invalid_token", domain="testserver")
        resp = client.post("/api/auth/refresh")
        assert resp.status_code == 401

    def test_refresh_token_rotation(self, client):
        login_resp = client.post(
            "/api/auth/login",
            json={"email": "admin@test.com", "password": "admin123"},
        )
        assert login_resp.status_code == 200
        first_refresh = login_resp.cookies["refresh_token"]

        resp1 = client.post("/api/auth/refresh")
        assert resp1.status_code == 200
        assert resp1.cookies["refresh_token"] != first_refresh

        client.cookies.clear()
        client.cookies.set("refresh_token", first_refresh, domain="testserver")
        resp2 = client.post("/api/auth/refresh")
        assert resp2.status_code == 401

    def test_refresh_requires_cookie(self, client):
        # conftest 已预登录；清空 cookie 构造"无刷新令牌"请求
        saved = dict(client.cookies)
        client.cookies.clear()
        try:
            resp = client.post("/api/auth/refresh")
        finally:
            client.cookies.update(saved)
        assert resp.status_code == 401

    def test_refresh_rotates_cookie(self, client):
        login = client.post(
            "/api/auth/login",
            json={"email": "admin@test.com", "password": "admin123"},
        )
        assert login.status_code == 200
        assert login.json()["refresh_token"] == ""
        assert "refresh_token" in login.cookies
        old = login.cookies["refresh_token"]
        resp = client.post("/api/auth/refresh")
        assert resp.status_code == 200
        assert resp.cookies["refresh_token"] != old


class TestAuthRegister:
    @patch("routers.auth.register._generate_code", return_value="654321")
    def test_register_flow(self, mock_gen_code, client):
        resp = client.post(
            "/api/auth/send-register-code", json={"email": "newuser@test.com"}
        )
        assert resp.status_code == 200

        resp = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@test.com",
                "code": "654321",
                "password": "StrongPass@1",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data

    def test_register_wrong_code(self, client):
        with patch(
            "routers.auth.register._generate_code", return_value="654321"
        ):
            client.post(
                "/api/auth/send-register-code",
                json={"email": "wrongcode@test.com"},
            )
        resp = client.post(
            "/api/auth/register",
            json={
                "email": "wrongcode@test.com",
                "code": "000000",
                "password": "StrongPass@1",
            },
        )
        assert resp.status_code == 400

    def test_register_weak_password(self, client):
        with patch(
            "routers.auth.register._generate_code", return_value="123456"
        ):
            client.post(
                "/api/auth/send-register-code",
                json={"email": "weakpass@test.com"},
            )
        resp = client.post(
            "/api/auth/register",
            json={
                "email": "weakpass@test.com",
                "code": "123456",
                "password": "12345678",
            },
        )
        assert resp.status_code == 400

    @patch("routers.auth.register._generate_code", return_value="654321")
    def test_register_flow_complete(self, mock_gen_code, client):
        resp = client.post(
            "/api/auth/send-register-code", json={"email": "flowtest@test.com"}
        )
        assert resp.status_code == 200

        resp = client.post(
            "/api/auth/register",
            json={
                "email": "flowtest@test.com",
                "code": "654321",
                "password": "StrongPass@1",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "flowtest@test.com"

    def test_password_policy_rejects_common(self, client):
        with patch(
            "routers.auth.register._generate_code", return_value="654321"
        ):
            client.post(
                "/api/auth/send-register-code",
                json={"email": "commonpass@test.com"},
            )
        resp = client.post(
            "/api/auth/register",
            json={
                "email": "commonpass@test.com",
                "code": "654321",
                "password": "password123",
            },
        )
        assert resp.status_code == 400

    def test_password_policy_rejects_short(self, client):
        with patch(
            "routers.auth.register._generate_code", return_value="654321"
        ):
            client.post(
                "/api/auth/send-register-code",
                json={"email": "shortpass@test.com"},
            )
        resp = client.post(
            "/api/auth/register",
            json={
                "email": "shortpass@test.com",
                "code": "654321",
                "password": "Abc1!",
            },
        )
        assert resp.status_code == 400

    def test_register_duplicate(self, client):
        with patch(
            "routers.auth.register._generate_code", return_value="123456"
        ):
            with patch(
                "routers.auth.register.get_user_by_email",
                return_value=None,
            ):
                client.post(
                    "/api/auth/send-register-code",
                    json={"email": "admin@test.com"},
                )
        resp = client.post(
            "/api/auth/register",
            json={
                "email": "admin@test.com",
                "code": "123456",
                "password": "StrongPass@1",
            },
        )
        assert resp.status_code == 409

    def test_register_password_complexity_edge(self, client):
        with patch(
            "routers.auth.register._generate_code", return_value="654321"
        ):
            client.post(
                "/api/auth/send-register-code",
                json={"email": "edgepass@test.com"},
            )
        resp = client.post(
            "/api/auth/register",
            json={
                "email": "edgepass@test.com",
                "code": "654321",
                "password": "Ab1!xyzw",
            },
        )
        assert resp.status_code == 201


class TestAuthPassword:
    def test_forgot_password(self, client):
        resp = client.post(
            "/api/auth/forgot-password", json={"email": "admin@test.com"}
        )
        assert resp.status_code == 200

    @patch(
        "routers.auth.password._generate_code", return_value="999999"
    )
    def test_reset_password(self, mock_gen_code, client):
        client.post(
            "/api/auth/forgot-password", json={"email": "admin@test.com"}
        )
        resp = client.post(
            "/api/auth/reset-password",
            json={
                "email": "admin@test.com",
                "code": "999999",
                "new_password": "NewStr0ng@Pass",
            },
        )
        assert resp.status_code == 200

    def test_reset_wrong_code(self, client):
        with patch(
            "routers.auth.password._generate_code", return_value="111111"
        ):
            client.post(
                "/api/auth/forgot-password", json={"email": "admin@test.com"}
            )
        resp = client.post(
            "/api/auth/reset-password",
            json={
                "email": "admin@test.com",
                "code": "999999",
                "new_password": "NewStr0ng@Pass",
            },
        )
        assert resp.status_code == 400

    def test_change_password(self, client):
        from unittest.mock import AsyncMock, MagicMock

        import bcrypt
        mock_user = MagicMock()
        mock_user.id = "u-change-legacy"
        mock_user.password_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
        mock_user.email = "change-legacy@test.com"
        with patch("routers.auth.password.get_user_by_id", new_callable=AsyncMock, return_value=mock_user), \
             patch("routers.auth.password.update_password", new_callable=AsyncMock), \
             patch("routers.auth.password.revoke_all_user_tokens", new_callable=AsyncMock), \
             patch("routers.auth.password.send_email", new_callable=AsyncMock):
            resp = client.post(
                "/api/auth/change-password",
                json={
                    "old_password": "admin123",
                    "new_password": "NewStr0ng@Pass",
                },
            )
            assert resp.status_code == 200

    def test_forgot_password_nonexistent_email(self, client):
        resp = client.post(
            "/api/auth/forgot-password", json={"email": "doesnotexist@test.com"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data

    def test_reset_password_expired_code(self, client):
        resp = client.post(
            "/api/auth/reset-password",
            json={
                "email": "ghost@test.com",
                "code": "000000",
                "new_password": "NewStr0ng@Pass",
            },
        )
        assert resp.status_code == 400


class TestAuthProfile:
    def test_get_profile(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "admin@test.com"
        assert data["is_verified"] is True

    def test_profile_returns_admin_in_legacy(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] is not None
        assert data["email"] is not None
        assert isinstance(data["roles"], list)
        assert "admin" in data["roles"]
        assert data["is_verified"] is True


class TestAuthForgotPasswordFlow:

    @patch("routers.auth.register._generate_code", return_value="112233")
    @patch("routers.auth.password._generate_code", return_value="445566")
    def test_forgot_password_full_flow(self, mock_pwd_code, mock_reg_code, client):
        client.post(
            "/api/auth/send-register-code", json={"email": "fpflow@test.com"}
        )
        reg_resp = client.post(
            "/api/auth/register",
            json={
                "email": "fpflow@test.com",
                "code": "112233",
                "password": "StrongPass@1",
            },
        )
        assert reg_resp.status_code == 201

        forgot_resp = client.post(
            "/api/auth/forgot-password", json={"email": "fpflow@test.com"}
        )
        assert forgot_resp.status_code == 200

        reset_resp = client.post(
            "/api/auth/reset-password",
            json={
                "email": "fpflow@test.com",
                "code": "445566",
                "new_password": "NewStr0ng@Pass",
            },
        )
        assert reset_resp.status_code == 200
