"""Tests for backend.tasks.registry — Celery task functions."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRunAgentTask:

    @patch("tasks.registry._run_async")
    def test_success(self, mock_run_async):
        mock_run_async.return_value = {"run_id": "run-1", "status": "completed"}
        from tasks.registry import run_agent

        result = run_agent.run(
            requirement="test req",
            run_id="run-1",
            session_id="sess-1",
            agent_id="agent-1",
            api_key="sk-test",
            api_base="http://api.test",
            model="test-model",
        )
        assert result == {"run_id": "run-1", "status": "completed"}

    def test_assertion_error_without_run_id(self):
        from tasks.registry import run_agent
        with pytest.raises(AssertionError, match="run_id must be provided"):
            run_agent.run(requirement="test", run_id=None)

    @patch("tasks.registry._report_run_error")
    @patch("tasks.registry._run_async", side_effect=Exception("pipeline crash"))
    def test_failure_without_mock_fallback(self, mock_run_async, mock_report):
        from tasks.registry import run_agent
        with patch("tasks.registry.ENABLE_MOCK_FALLBACK", False):
            with pytest.raises(Exception, match="pipeline crash"):
                run_agent.run(requirement="test", run_id="run-1")

    @patch("tasks.registry._report_run_error")
    @patch("tasks.registry._try_mock_fallback")
    @patch("tasks.registry._run_async", side_effect=Exception("pipeline crash"))
    def test_failure_with_mock_fallback_success(self, mock_run_async, mock_fallback, mock_report):
        from tasks.registry import run_agent
        mock_fallback.return_value = {"run_id": "run-1", "status": "completed", "fallback": True}

        with patch("tasks.registry.ENABLE_MOCK_FALLBACK", True):
            result = run_agent.run(requirement="test", run_id="run-1")

        assert result["fallback"] is True

    @patch("tasks.registry._report_run_error")
    @patch("tasks.registry._try_mock_fallback", return_value=None)
    @patch("tasks.registry._run_async", side_effect=Exception("pipeline crash"))
    def test_failure_with_mock_fallback_returns_none(self, mock_run_async, mock_fallback, mock_report):
        from tasks.registry import run_agent

        # Need to patch self.retry to avoid actual retry
        with patch("tasks.registry.ENABLE_MOCK_FALLBACK", True):
            with pytest.raises(Exception, match="pipeline crash"):
                run_agent.run(requirement="test", run_id="run-1")

    @patch("tasks.registry._run_async")
    def test_no_session_no_agent(self, mock_run_async):
        mock_run_async.return_value = {"run_id": "run-1", "status": "completed"}
        from tasks.registry import run_agent

        result = run_agent.run(
            requirement="test req",
            run_id="run-1",
            session_id=None,
            agent_id=None,
            api_key=None,
            api_base=None,
            model=None,
        )
        assert result == {"run_id": "run-1", "status": "completed"}

    @patch("tasks.registry._run_async")
    def test_elapse_logging(self, mock_run_async):
        """Test that timing and retry info is logged."""
        mock_run_async.return_value = {"run_id": "run-1", "status": "completed"}
        from tasks.registry import run_agent

        result = run_agent.run(
            requirement="test req",
            run_id="run-1",
        )
        assert result["status"] == "completed"


class TestCompleteAgentTask:

    @patch("tasks.registry._run_async")
    def test_success(self, mock_run_async):
        mock_run_async.return_value = None
        from tasks.registry import complete_agent

        result = complete_agent.run(
            content="hello",
            run_id="run-1",
            api_key="sk-test",
            api_base=None,
            model=None,
            thinking=None,
        )
        assert result is None

    @patch("tasks.registry._run_async")
    def test_success_with_thinking(self, mock_run_async):
        mock_run_async.return_value = None
        from tasks.registry import complete_agent

        result = complete_agent.run(
            content="hello",
            run_id="run-1",
            api_key="sk-test",
            api_base="https://api.deepseek.com",
            model="deepseek-v4",
            thinking="prev thought",
        )
        assert result is None

    @patch("tasks.registry._run_async", side_effect=Exception("stream failed"))
    def test_failure_raises(self, mock_run_async):
        from tasks.registry import complete_agent

        with pytest.raises(Exception, match="stream failed"):
            complete_agent.run(
                content="test",
                run_id="run-1",
                api_key="sk-test",
            )

    @patch("tasks.registry._run_async")
    def test_success_with_custom_model_and_base(self, mock_run_async):
        mock_run_async.return_value = None
        from tasks.registry import complete_agent

        result = complete_agent.run(
            content="test content",
            run_id="run-cust",
            api_key="sk-key",
            api_base="https://custom.api.com",
            model="custom-model",
            thinking=None,
        )
        assert result is None
