"""Unit tests for backend/routers/auth/schemas.py (Pydantic request/response models)."""

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError


@pytest.mark.requirement("REQ-AUTH-001")
class TestAuthSchemas:
    def test_login_request_defaults(self):
        from routers.auth.schemas import LoginRequest

        req = LoginRequest(email="test@example.com", password="pass")
        assert req.remember_me is False

    def test_login_request_remember_me_true(self):
        from routers.auth.schemas import LoginRequest

        req = LoginRequest(email="test@example.com", password="pass", remember_me=True)
        assert req.remember_me is True

    def test_register_request_valid(self):
        from routers.auth.schemas import RegisterRequest

        req = RegisterRequest(email="a@b.com", code="123456", password="Str0ng!Pass")
        assert req.email == "a@b.com"
        assert req.code == "123456"
        assert req.password == "Str0ng!Pass"

    def test_register_request_missing_field(self):
        from routers.auth.schemas import RegisterRequest

        with pytest.raises(ValidationError):
            RegisterRequest(email="a@b.com", code="123456")

    def test_email_validation_rejects_invalid(self):
        from routers.auth.schemas import SendRegisterCodeRequest

        with pytest.raises(ValidationError):
            SendRegisterCodeRequest(email="not-an-email")

    def test_auth_response_default_token_type(self):
        from routers.auth.schemas import AuthResponse, UserResponse

        user = UserResponse(id="u1", email="a@b.com", roles=["admin"], is_verified=True, username=None)
        resp = AuthResponse(
            access_token="token",
            refresh_token="refresh",
            expires_in=900,
            user=user,
        )
        assert resp.token_type == "bearer"

    def test_user_response_optional_username(self):
        from routers.auth.schemas import UserResponse

        user = UserResponse(id="u1", email="a@b.com", roles=[], is_verified=False, username=None)
        assert user.username is None

    def test_user_response_with_username(self):
        from routers.auth.schemas import UserResponse

        user = UserResponse(id="u1", email="a@b.com", username="alice", roles=["user"], is_verified=True)
        assert user.username == "alice"

    def test_refresh_request(self):
        from routers.auth.schemas import RefreshRequest

        req = RefreshRequest(refresh_token="rtok")
        assert req.refresh_token == "rtok"

    def test_forgot_password_request(self):
        from routers.auth.schemas import ForgotPasswordRequest

        req = ForgotPasswordRequest(email="user@example.com")
        assert req.email == "user@example.com"

    def test_reset_password_request(self):
        from routers.auth.schemas import ResetPasswordRequest

        req = ResetPasswordRequest(email="user@ex.com", code="654321", new_password="NewPass1!")
        assert req.new_password == "NewPass1!"

    def test_logout_request(self):
        from routers.auth.schemas import LogoutRequest

        req = LogoutRequest(refresh_token="tok")
        assert req.refresh_token == "tok"

    def test_change_password_request(self):
        from routers.auth.schemas import ChangePasswordRequest

        req = ChangePasswordRequest(old_password="old", new_password="new")
        assert req.old_password == "old"
        assert req.new_password == "new"

    def test_merge_request(self):
        from routers.auth.schemas import MergeRequest

        req = MergeRequest(guest_id="guest-uuid")
        assert req.guest_id == "guest-uuid"

    def test_verify_request(self):
        from routers.auth.schemas import VerifyRequest

        req = VerifyRequest(email="a@b.com", code="000000")
        assert req.email == "a@b.com"
        assert req.code == "000000"

    def test_message_response(self):
        from routers.auth.schemas import MessageResponse

        resp = MessageResponse(message="ok")
        assert resp.message == "ok"

    def test_email_hint_response(self):
        from routers.auth.schemas import EmailHintResponse

        resp = EmailHintResponse(message="sent", email_hint="u***@example.com")
        assert resp.email_hint == "u***@example.com"

    def test_auth_config_response(self):
        from routers.auth.schemas import AuthConfigResponse

        resp = AuthConfigResponse(enabled=True, mode="rbac")
        assert resp.enabled is True
        assert resp.mode == "rbac"




@pytest.mark.requirement("REQ-AUTH-001")
class TestAuthHelpers:
    def test_generate_code_returns_six_digits(self):
        from routers.auth.schemas import _generate_code

        code = _generate_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_generate_code_multiple_calls_differ(self):
        from routers.auth.schemas import _generate_code

        codes = {_generate_code() for _ in range(20)}
        assert len(codes) > 1

    def test_mask_email_typical(self):
        from routers.auth.schemas import _mask_email

        assert _mask_email("user@example.com") == "u***@example.com"

    def test_mask_email_short_local(self):
        from routers.auth.schemas import _mask_email

        assert _mask_email("a@b.com") == "a***@b.com"

    def test_mask_email_single_char(self):
        from routers.auth.schemas import _mask_email

        result = _mask_email("x@y.com")
        assert result == "x***@y.com"

    def test_client_ip_with_forwarded(self):
        from routers.auth.schemas import _client_ip

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "203.0.113.1, 10.0.0.1"}
        result = _client_ip(mock_request)
        assert result == "203.0.113.1"

    def test_client_ip_without_forwarded(self):
        from routers.auth.schemas import _client_ip

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client.host = "192.168.1.1"
        result = _client_ip(mock_request)
        assert result == "192.168.1.1"

    def test_client_ip_no_client(self):
        from routers.auth.schemas import _client_ip

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = None
        result = _client_ip(mock_request)
        assert result == "unknown"


# ─────────────────────────────────────────────────────────────────────
# 7. backend/services/run_service.py — RunService
# ─────────────────────────────────────────────────────────────────────


