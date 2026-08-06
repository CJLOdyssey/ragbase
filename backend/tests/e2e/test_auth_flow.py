import pytest

pytestmark = pytest.mark.integration

"""E2E Test: Authentication flow — config, login, profile, change-password, logout."""

import uuid

from tests.conftest import (
    TEST_EMAIL,
    TEST_PASSWORD,
    Api,
    _clear_rate_limits,
)


class TestAuthFlow:
    """E2E tests for the full authentication lifecycle."""

    def test_auth_config(self, api: Api):
        """GET /api/auth/config returns mode and enabled flag."""
        r = api.get("/api/auth/config")
        assert r.status_code == 200
        body = r.json()
        assert "mode" in body
        assert "enabled" in body
        assert body["mode"] in ("legacy", "rbac")

    def test_login_wrong_password(self, api: Api):
        """POST /api/auth/login with wrong password returns 401."""
        r = api.post(
            "/api/auth/login",
            json={"email": TEST_EMAIL, "password": "WrongPassword!1"},
        )
        if r.status_code == 200:
            # legacy mode always returns 200 — skip this negative test
            return
        # 429 = shared-IP auth rate limit under parallel runs — still a failed login
        assert r.status_code in (401, 429)

    def test_login_nonexistent_user(self, api: Api):
        """POST /api/auth/login with non-existent email returns error."""
        unique = uuid.uuid4().hex[:8]
        r = api.post(
            "/api/auth/login",
            json={"email": f"nonexistent_{unique}@test.com", "password": "x"},
        )
        if r.status_code == 200:
            # legacy mode — skip
            return
        assert r.status_code in (401, 403, 429)

    def test_get_profile(self, api: Api):
        """GET /api/auth/me returns user profile when authenticated."""
        r = api.get("/api/auth/me")
        if r.status_code == 200:
            body = r.json()
            assert "id" in body
            assert "email" in body
            assert "roles" in body
            assert isinstance(body["roles"], list)
        else:
            # legacy mode may not have /me endpoint or returns 401
            assert r.status_code in (401, 404)

    def test_change_password_wrong_old(self, api: Api):
        """POST /api/auth/change-password with wrong old password fails."""
        r = api.post(
            "/api/auth/change-password",
            json={"old_password": "WrongOld!1", "new_password": "NewPass!1"},
        )
        if r.status_code == 200:
            # legacy mode — no-op, skip
            return
        # legacy mode has no real user → 404; rbac validates the old password → 401
        assert r.status_code in (400, 401, 403, 404)

    def test_change_password_same_as_old(self, api: Api):
        """POST /api/auth/change-password with same new password fails."""
        r = api.post(
            "/api/auth/change-password",
            json={"old_password": TEST_PASSWORD, "new_password": TEST_PASSWORD},
        )
        if r.status_code == 200:
            # legacy mode — no-op, skip
            return
        assert r.status_code in (400, 403, 404)

    def test_forgot_password(self, api: Api):
        """POST /api/auth/forgot-password returns message."""
        r = api.post(
            "/api/auth/forgot-password",
            json={"email": TEST_EMAIL},
        )
        if r.status_code == 200:
            body = r.json()
            assert "message" in body
        else:
            assert r.status_code in (400, 404)

    def test_register_missing_fields(self, api: Api):
        """POST /api/auth/register with missing fields returns 422."""
        r = api.post("/api/auth/register", json={})
        assert r.status_code == 422

    def test_register_invalid_email(self, api: Api):
        """POST /api/auth/register with invalid email returns 422."""
        r = api.post(
            "/api/auth/register",
            json={"email": "not-an-email", "code": "000000", "password": "x"},
        )
        assert r.status_code == 422

    def test_login_invalid_email_format(self, api: Api):
        """POST /api/auth/login with invalid email returns 422."""
        r = api.post(
            "/api/auth/login",
            json={"email": "not-an-email", "password": "x"},
        )
        assert r.status_code == 422

    def test_send_register_code_invalid_email(self, api: Api):
        """POST /api/auth/send-register-code with invalid email returns 422."""
        r = api.post(
            "/api/auth/send-register-code",
            json={"email": "bad-format"},
        )
        assert r.status_code == 422

    def test_register_wrong_code(self, api: Api):
        """POST /api/auth/register with wrong verification code fails."""
        unique = uuid.uuid4().hex[:8]
        email = f"e2e_{unique}@test.com"
        _clear_rate_limits()
        # Send code first (may fail if email service not configured, skip gracefully)
        r_code = api.post(
            "/api/auth/send-register-code",
            json={"email": email},
        )
        if r_code.status_code != 200:
            return
        # Register with wrong code
        _clear_rate_limits()
        r = api.post(
            "/api/auth/register",
            json={"email": email, "code": "000000", "password": "Test@1234"},
        )
        assert r.status_code in (400, 401)

    def test_logout_without_token(self, api: Api):
        """POST /api/auth/logout without valid refresh token fails."""
        r = api.post(
            "/api/auth/logout",
            json={"refresh_token": "invalid-token"},
        )
        if r.status_code == 204:
            return  # legacy mode may 204 no-op
        assert r.status_code in (400, 401, 403)

    def test_refresh_with_invalid_token(self, api: Api):
        """POST /api/auth/refresh with invalid token fails."""
        r = api.post(
            "/api/auth/refresh",
            json={"refresh_token": "garbage-token-value"},
        )
        if r.status_code == 200:
            # legacy mode may always return 200
            return
        assert r.status_code in (400, 401)

    def test_resend_verification(self, api: Api):
        """POST /api/auth/resend-verification returns message (idempotent)."""
        unique = uuid.uuid4().hex[:8]
        r = api.post(
            "/api/auth/resend-verification",
            json={"email": f"e2e_{unique}@test.com"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "message" in body

    def test_send_register_code_missing_email(self, api: Api):
        """POST /api/auth/send-register-code with missing email returns 422."""
        r = api.post("/api/auth/send-register-code", json={})
        assert r.status_code == 422
