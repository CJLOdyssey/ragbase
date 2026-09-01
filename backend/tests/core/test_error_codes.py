"""Unit tests for core.error_codes (ErrorCode enum + error_response mapping)."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException


class TestErrorCode:
    def test_enum_values_are_strings(self):
        from core.error_codes import ErrorCode

        assert ErrorCode.AGENT_NOT_FOUND.value == "AGENT_001"
        assert ErrorCode.AUTH_TOKEN_EXPIRED.value == "AUTH_003"
        assert ErrorCode.RATE_LIMITED.value == "RATE_001"
        assert ErrorCode.INTERNAL_ERROR.value == "GENERAL_001"

    def test_enum_is_str_enum(self):
        from core.error_codes import ErrorCode

        assert isinstance(ErrorCode.INVALID_REQUEST, str)
        assert ErrorCode.INVALID_REQUEST == "GENERAL_002"

    def test_all_codes_have_unique_values(self):
        from core.error_codes import ErrorCode

        values = [e.value for e in ErrorCode]
        assert len(values) == len(set(values))




class TestErrorResponse:
    def test_returns_http_exception(self):
        from core.error_codes import ErrorCode, error_response

        exc = error_response(ErrorCode.TEAM_NOT_FOUND, detail="Team missing")
        assert isinstance(exc, HTTPException)
        assert exc.status_code == 404

    def test_detail_structure(self):
        from core.error_codes import ErrorCode, error_response

        exc = error_response(ErrorCode.AUTH_UNAUTHORIZED, detail="Bad token")
        detail = exc.detail
        assert detail["error"]["code"] == "AUTH_001"
        assert detail["error"]["message"] == "Bad token"

    def test_default_message_from_enum_name(self):
        from core.error_codes import ErrorCode, error_response

        exc = error_response(ErrorCode.RATE_LIMITED)
        assert exc.detail["error"]["message"] == "Rate Limited"

    @pytest.mark.parametrize(
        "code,expected_status",
        [
            ("AGENT_NOT_FOUND", 404),
            ("AUTH_UNAUTHORIZED", 401),
            ("AUTH_INSUFFICIENT_ROLE", 403),
            ("TEAM_CONFLICT", 409),
            ("RATE_LIMITED", 429),
            ("ATTACHMENT_TOO_LARGE", 413),
            ("ATTACHMENT_TYPE_INVALID", 415),
            ("ATTACHMENT_FILE_MISSING", 410),
            ("INTERNAL_ERROR", 500),
            ("INVALID_REQUEST", 400),
            ("AUTH_ACCOUNT_LOCKED", 423),
        ],
    )
    def test_status_codes(self, code, expected_status):
        from core.error_codes import ErrorCode, error_response

        exc = error_response(getattr(ErrorCode, code))
        assert exc.status_code == expected_status

    def test_unknown_code_falls_back_to_500(self):
        from core.error_codes import _STATUS_MAP, ErrorCode, error_response

        code = ErrorCode.AGENT_NOT_FOUND
        with patch.dict(_STATUS_MAP, clear=True):
            exc = error_response(code)
        assert exc.status_code == 500


