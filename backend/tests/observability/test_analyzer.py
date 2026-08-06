"""Tests for backend/observability/analyzer.py — analyze_error, analyze_trace, recent_errors_report."""

from unittest.mock import MagicMock, patch

import pytest


class TestAnalyzeError:
    def test_known_error_returns_suggestion(self):
        from observability.analyzer import analyze_error

        result = analyze_error("TypeError")
        assert result is not None
        assert "类型错误" in result

    def test_unknown_error_returns_none(self):
        from observability.analyzer import analyze_error

        result = analyze_error("SomeWeirdError")
        assert result is None

    def test_substring_match(self):
        from observability.analyzer import analyze_error

        result = analyze_error("django.db.utils.ProgrammingError: relation does not exist")
        assert result is not None
        assert "SQL" in result

    def test_all_known_errors(self):
        from observability.analyzer import analyze_error

        for key in [
            "UndefinedTable",
            "ProgrammingError",
            "InterfaceError",
            "TimeoutError",
            "ConnectionRefusedError",
            "KeyError",
            "TypeError",
            "AuthenticationError",
        ]:
            assert analyze_error(key) is not None, f"{key} should return a suggestion"

    def test_empty_string_returns_none(self):
        from observability.analyzer import analyze_error

        assert analyze_error("") is None

    def test_operational_error_with_leading_space(self):
        from observability.analyzer import analyze_error

        result = analyze_error(" OperationalError")
        assert result is not None
        assert "连接" in result


class TestAnalyzeTrace:
    def test_empty_trace_returns_empty_events(self):
        from observability.analyzer import analyze_trace

        mock_store = MagicMock()
        mock_store.by_trace.return_value = []
        with patch("observability.analyzer.get_store", return_value=mock_store):
            result = analyze_trace("empty-trace")
            assert result["trace_id"] == "empty-trace"
            assert result["events"] == []
            assert result["suggestion"] is None

    def test_trace_with_no_errors(self):
        from observability.analyzer import analyze_trace

        mock_store = MagicMock()
        mock_store.by_trace.return_value = [
            {"error_type": "", "duration_ms": 500, "level": "INFO", "message": "ok", "error_stack": None, "logger": "test"},
        ]
        with patch("observability.analyzer.get_store", return_value=mock_store):
            result = analyze_trace("no-errors")
            assert result["total_events"] == 1
            assert result["errors"] == 0
            assert result["slow_spans"] == 0
            assert result["suggestion"] is None

    def test_trace_with_errors(self):
        from observability.analyzer import analyze_trace

        mock_store = MagicMock()
        mock_store.by_trace.return_value = [
            {"error_type": "TypeError", "duration_ms": 0, "level": "ERROR", "message": "bad type", "error_stack": "trace...", "logger": "test"},
        ]
        with patch("observability.analyzer.get_store", return_value=mock_store):
            result = analyze_trace("has-errors")
            assert result["errors"] == 1
            assert len(result["error_events"]) == 1
            assert result["error_events"][0]["message"] == "bad type"
            assert result["suggestion"] is not None

    def test_trace_with_slow_events(self):
        from observability.analyzer import analyze_trace

        mock_store = MagicMock()
        mock_store.by_trace.return_value = [
            {"error_type": "", "duration_ms": 5000, "level": "INFO", "message": "slow", "error_stack": None, "logger": "test"},
        ]
        with patch("observability.analyzer.get_store", return_value=mock_store):
            result = analyze_trace("slow-trace")
            assert result["slow_spans"] == 1
            assert len(result["slow_events"]) == 1
            assert result["slow_events"][0]["duration_ms"] == 5000

    def test_trace_truncates_error_stack(self):
        from observability.analyzer import analyze_trace

        mock_store = MagicMock()
        long_stack = "x" * 600
        mock_store.by_trace.return_value = [
            {"error_type": "KeyError", "duration_ms": 0, "level": "ERROR", "message": "missing key", "error_stack": long_stack, "logger": "test"},
        ]
        with patch("observability.analyzer.get_store", return_value=mock_store):
            result = analyze_trace("long-stack")
            assert len(result["error_events"][0]["error_stack"]) <= 500

    def test_trace_limits_errors_to_10(self):
        from observability.analyzer import analyze_trace

        mock_store = MagicMock()
        mock_store.by_trace.return_value = [
            {"error_type": "KeyError", "duration_ms": 0, "level": "ERROR", "message": str(i), "error_stack": None, "logger": "test"}
            for i in range(15)
        ]
        with patch("observability.analyzer.get_store", return_value=mock_store):
            result = analyze_trace("many-errors")
            assert len(result["error_events"]) == 10

    def test_trace_limits_slow_to_10(self):
        from observability.analyzer import analyze_trace

        mock_store = MagicMock()
        mock_store.by_trace.return_value = [
            {"error_type": "", "duration_ms": 2000, "level": "INFO", "message": str(i), "error_stack": None, "logger": "test"}
            for i in range(15)
        ]
        with patch("observability.analyzer.get_store", return_value=mock_store):
            result = analyze_trace("many-slow")
            assert len(result["slow_events"]) == 10

    def test_trace_no_suggestion_for_unrecognized_error(self):
        from observability.analyzer import analyze_trace

        mock_store = MagicMock()
        mock_store.by_trace.return_value = [
            {"error_type": "BogusError", "duration_ms": 0, "level": "ERROR", "message": "x", "error_stack": None, "logger": "test"},
        ]
        with patch("observability.analyzer.get_store", return_value=mock_store):
            result = analyze_trace("bogus")
            assert result["suggestion"] is None

    def test_trace_with_connected_upper_error_type(self):
        from observability.analyzer import analyze_trace

        mock_store = MagicMock()
        mock_store.by_trace.return_value = [
            {"error_type": "DatabaseConnectionRefusedError", "duration_ms": 0, "level": "ERROR", "message": "connection failed", "error_stack": None, "logger": "db"},
        ]
        with patch("observability.analyzer.get_store", return_value=mock_store):
            result = analyze_trace("conn-refused")
            assert result["errors"] == 1
            # "ConnectionRefusedError" is a substring of "DatabaseConnectionRefusedError"
            assert result["suggestion"] is not None


class TestRecentErrorsReport:
    def test_no_errors_returns_empty_list(self):
        from observability.analyzer import recent_errors_report

        mock_store = MagicMock()
        mock_store.error_trace_ids.return_value = []
        with patch("observability.analyzer.get_store", return_value=mock_store):
            result = recent_errors_report()
            assert result == []

    def test_skips_traces_with_zero_errors(self):
        from observability.analyzer import recent_errors_report

        mock_store = MagicMock()
        mock_store.error_trace_ids.return_value = [{"trace_id": "t1"}]
        # Return events with no error_type (errors=0), so the report filter skips it
        mock_store.by_trace.return_value = [
            {"error_type": "", "duration_ms": 0, "level": "INFO", "message": "ok", "error_stack": None, "logger": "test"},
        ]
        with patch("observability.analyzer.get_store", return_value=mock_store):
            result = recent_errors_report()
            assert result == []

    def test_includes_traces_with_errors(self):
        from observability.analyzer import recent_errors_report

        mock_store = MagicMock()
        mock_store.error_trace_ids.return_value = [{"trace_id": "t1"}]
        mock_store.by_trace.return_value = [
            {"error_type": "TypeError", "duration_ms": 0, "level": "ERROR", "message": "bad", "error_stack": None, "logger": "test"},
        ]
        with patch("observability.analyzer.get_store", return_value=mock_store):
            result = recent_errors_report()
            assert len(result) == 1
            assert result[0]["trace_id"] == "t1"

    def test_limits_traces_to_20(self):
        from observability.analyzer import recent_errors_report

        mock_store = MagicMock()
        mock_store.error_trace_ids.return_value = [{"trace_id": f"t{i}"} for i in range(30)]
        mock_store.by_trace.return_value = [
            {"error_type": "KeyError", "duration_ms": 0, "level": "ERROR", "message": "x", "error_stack": None, "logger": "test"},
        ]
        with patch("observability.analyzer.get_store", return_value=mock_store):
            result = recent_errors_report()
            assert len(result) == 20

    def test_custom_seconds_passed_through(self):
        from observability.analyzer import recent_errors_report

        mock_store = MagicMock()
        mock_store.error_trace_ids.return_value = []
        with patch("observability.analyzer.get_store", return_value=mock_store):
            recent_errors_report(seconds=600)
            mock_store.error_trace_ids.assert_called_once_with(seconds=600)
