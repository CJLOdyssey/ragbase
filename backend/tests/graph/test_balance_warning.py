"""Tests for balance insufficient warning detection."""

from unittest.mock import AsyncMock, patch

import pytest
from tasks.pipeline_utils import _is_balance_error


class TestIsBalanceError:
    @pytest.mark.parametrize("error_msg", [
        "insufficient_quota: you have exceeded your quota",
        "Insufficient balance: your account balance is low",
        "余额不足，请充值",
        "Billing limit reached for this API key",
        "quota exceeded for model gpt-4",
        "Payment required: 402",
        "你的账户余额不足，无法调用此模型",
        "account balance is too low",
        "402 Payment Required",
    ])
    def test_detects_balance_errors(self, error_msg: str):
        assert _is_balance_error(Exception(error_msg))

    @pytest.mark.parametrize("error_msg", [
        "rate limit exceeded",
        "invalid API key",
        "timeout error",
        "internal server error",
        "model not found",
        "connection refused",
        "bad request",
        "unauthorized",
    ])
    def test_ignores_non_balance_errors(self, error_msg: str):
        assert not _is_balance_error(Exception(error_msg))

    def test_empty_error_message(self):
        assert not _is_balance_error(Exception(""))

    def test_case_insensitive_matching(self):
        assert _is_balance_error(Exception("INSUFFICIENT_BALANCE"))


class TestReportRunErrorBalance:
    @patch("tasks.pipeline_utils.publish_run_message")
    @patch("tasks.pipeline_utils.update_run_status")
    def test_publishes_balance_warning_on_balance_error(
        self, mock_update_status: AsyncMock, mock_publish: AsyncMock
    ):
        from tasks.pipeline_utils import _report_run_error

        exc = Exception("insufficient_quota: no money")
        _report_run_error("run-123", exc)

        balance_calls = [
            c for c in mock_publish.call_args_list
            if c[0][1].get("type") == "balance_warning"
        ]
        assert len(balance_calls) == 1
        assert "余额不足" in balance_calls[0][0][1]["content"]

    @patch("tasks.pipeline_utils.publish_run_message")
    @patch("tasks.pipeline_utils.update_run_status")
    def test_does_not_publish_balance_warning_on_other_errors(
        self, mock_update_status: AsyncMock, mock_publish: AsyncMock
    ):
        from tasks.pipeline_utils import _report_run_error

        exc = Exception("rate limit exceeded")
        _report_run_error("run-456", exc)

        balance_calls = [
            c for c in mock_publish.call_args_list
            if c[0][1].get("type") == "balance_warning"
        ]
        assert len(balance_calls) == 0
