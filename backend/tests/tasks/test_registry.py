"""Tests for backend.tasks.registry — Celery task functions."""
import logging
from unittest.mock import patch

import pytest
from celery.exceptions import Retry


class TestRunAgentTask:

    @patch("tasks.registry._run_async")
    def test_success(self, mock_run_async):
        mock_run_async.return_value = {"run_id": "run-1", "status": "completed"}
        from tasks.registry import run_agent

        result = run_agent.run(
            requirement="test req",
            run_id="run-1",
            session_id="sess-1",
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
            # Direct-call mode: patch self.retry to assert the retry path is
            # taken explicitly instead of relying on Celery internals.
            with patch.object(run_agent, "retry", side_effect=Retry) as mock_retry:
                with pytest.raises(Retry):
                    run_agent.run(requirement="test", run_id="run-1")
        mock_retry.assert_called_once()
        # The error is reported to the run before retrying.
        mock_report.assert_called_once()
        assert mock_report.call_args[0][0] == "run-1"

    @patch("tasks.registry._report_run_error")
    @patch("tasks.registry._try_mock_fallback")
    @patch("tasks.registry._run_async", side_effect=Exception("pipeline crash"))
    def test_failure_with_mock_fallback_success(self, mock_run_async, mock_fallback, mock_report):
        from tasks.registry import run_agent
        mock_fallback.return_value = {"run_id": "run-1", "status": "completed", "fallback": True}

        with patch("tasks.registry.ENABLE_MOCK_FALLBACK", True):
            result = run_agent.run(requirement="test", run_id="run-1")

        assert result["fallback"] is True
        # Fallback success short-circuits: no error report, no retry.
        mock_report.assert_not_called()

    @patch("tasks.registry._report_run_error")
    @patch("tasks.registry._try_mock_fallback", return_value=None)
    @patch("tasks.registry._run_async", side_effect=Exception("pipeline crash"))
    def test_failure_with_mock_fallback_returns_none(self, mock_run_async, mock_fallback, mock_report):
        from tasks.registry import run_agent

        with patch("tasks.registry.ENABLE_MOCK_FALLBACK", True):
            with patch.object(run_agent, "retry", side_effect=Retry) as mock_retry:
                with pytest.raises(Retry):
                    run_agent.run(requirement="test", run_id="run-1")
        # Fallback returned None → error reported and task retried.
        mock_retry.assert_called_once()
        mock_report.assert_called_once()

    @patch("tasks.registry._run_async")
    def test_no_session_no_agent(self, mock_run_async):
        mock_run_async.return_value = {"run_id": "run-1", "status": "completed"}
        from tasks.registry import run_agent

        result = run_agent.run(
            requirement="test req",
            run_id="run-1",
            session_id=None,
            api_key=None,
            api_base=None,
            model=None,
        )
        assert result == {"run_id": "run-1", "status": "completed"}

    @patch("tasks.registry._run_async")
    def test_elapse_logging(self, mock_run_async, caplog):
        """SUCCESS 日志记录 elapsed 与 retry 信息。"""
        mock_run_async.return_value = {"run_id": "run-1", "status": "completed"}
        from tasks.registry import run_agent

        reg_logger = logging.getLogger("tasks.registry")
        reg_logger.propagate = True
        try:
            with caplog.at_level(logging.INFO, logger="tasks.registry"):
                result = run_agent.run(
                    requirement="test req",
                    run_id="run-1",
                )
        finally:
            reg_logger.propagate = False
        assert result["status"] == "completed"
        assert "Celery task SUCCESS" in caplog.text
        assert "run-1" in caplog.text


class TestIndexAssetTask:

    @patch("tasks.registry._run_async")
    def test_success_returns_chunk_count(self, mock_run_async):
        mock_run_async.return_value = {"indexed": True, "chunks": 7}
        from tasks.registry import index_asset

        result = index_asset.run(asset_id="a1", user_id="u1")
        assert result == {"indexed": True, "chunks": 7}

    @patch("tasks.registry._run_async", side_effect=Exception("embed 503"))
    def test_failure_retries(self, mock_run_async):
        """声明了 max_retries=2 就必须真的重试（瞬时故障恢复），而非直接失败。"""
        from tasks.registry import index_asset

        with patch.object(index_asset, "retry", side_effect=Retry) as mock_retry:
            with pytest.raises(Retry):
                index_asset.run(asset_id="a1", user_id="u1")
        mock_retry.assert_called_once()


def test_task_names_unique():
    """Celery 任务名全局唯一（重复注册会互相覆盖）。"""
    from tasks.registry import complete_agent, health_snapshot, index_asset, reindex_sweep, run_agent

    names = [
        t.name
        for t in (run_agent, index_asset, reindex_sweep, health_snapshot, complete_agent)
    ]
    assert len(names) == len(set(names))


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
