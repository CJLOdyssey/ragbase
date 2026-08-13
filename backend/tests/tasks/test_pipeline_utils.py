"""Tests for backend.tasks.pipeline_utils — all helper functions."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# =============================================================================
# log_memory_diff
# =============================================================================

class TestLogMemoryDiff:

    @pytest.fixture(autouse=True)
    def _reset_global_baseline(self):
        """log_memory_diff caches a module-global _baseline_snapshot.

        Restore it after each test so the mock baseline never leaks into
        other tests (e.g. test_agent_pipeline) that call log_memory_diff
        on the same worker under --dist=worksteal.
        """
        import tasks.pipeline_utils as pu

        yield
        pu._baseline_snapshot = None

    @patch("tasks.pipeline_utils.tracemalloc")
    def test_log_memory_diff_not_tracing(self, mock_tracemalloc):
        mock_tracemalloc.is_tracing.return_value = False
        from tasks.pipeline_utils import log_memory_diff
        log_memory_diff()

    @patch("tasks.pipeline_utils.tracemalloc")
    def test_log_memory_diff_first_snapshot(self, mock_tracemalloc):
        import tasks.pipeline_utils as pu
        mock_tracemalloc.is_tracing.return_value = True
        snapshot = MagicMock()
        mock_tracemalloc.take_snapshot.return_value = snapshot
        pu._baseline_snapshot = None
        from tasks.pipeline_utils import log_memory_diff
        log_memory_diff()
        assert pu._baseline_snapshot is snapshot

    @patch("tasks.pipeline_utils.tracemalloc")
    def test_log_memory_diff_subsequent_with_growth(self, mock_tracemalloc):
        import tasks.pipeline_utils as pu
        mock_tracemalloc.is_tracing.return_value = True
        baseline = MagicMock()
        pu._baseline_snapshot = baseline
        current = MagicMock()
        mock_tracemalloc.take_snapshot.return_value = current
        diff_item = MagicMock()
        diff_item.size_diff = 1000
        diff_item.__str__ = MagicMock(return_value="test diff line")
        current.compare_to.return_value = [diff_item]
        from tasks.pipeline_utils import log_memory_diff
        log_memory_diff()
        assert pu._baseline_snapshot is current

    @patch("tasks.pipeline_utils.tracemalloc")
    def test_log_memory_diff_no_growth(self, mock_tracemalloc):
        import tasks.pipeline_utils as pu
        mock_tracemalloc.is_tracing.return_value = True
        baseline = MagicMock()
        pu._baseline_snapshot = baseline
        current = MagicMock()
        mock_tracemalloc.take_snapshot.return_value = current
        diff_item = MagicMock()
        diff_item.size_diff = -100
        current.compare_to.return_value = [diff_item]
        from tasks.pipeline_utils import log_memory_diff
        log_memory_diff()
        assert pu._baseline_snapshot is current

    @patch("tasks.pipeline_utils.tracemalloc")
    def test_log_memory_diff_no_positive_diff(self, mock_tracemalloc):
        """All diff items have size_diff <= 0, so no growth logged."""
        import tasks.pipeline_utils as pu
        mock_tracemalloc.is_tracing.return_value = True
        baseline = MagicMock()
        pu._baseline_snapshot = baseline
        current = MagicMock()
        mock_tracemalloc.take_snapshot.return_value = current
        diff_neg = MagicMock()
        diff_neg.size_diff = 0
        current.compare_to.return_value = [diff_neg]
        from tasks.pipeline_utils import log_memory_diff
        log_memory_diff()
        assert pu._baseline_snapshot is current

    @patch("tasks.pipeline_utils.tracemalloc")
    def test_log_memory_diff_proc_read_error(self, mock_tracemalloc):
        """Lines 38-39: /proc read failure is silently ignored."""
        mock_tracemalloc.is_tracing.return_value = False
        with patch("tasks.pipeline_utils.os") as mock_os:
            mock_os.getpid.side_effect = OSError("no /proc")
            from tasks.pipeline_utils import log_memory_diff
            log_memory_diff()


# =============================================================================
# _run_async
# =============================================================================

class TestRunAsync:

    def test_run_async_executes_coroutine(self):
        async def my_coro():
            return 42
        from tasks.pipeline_utils import _run_async
        result = _run_async(my_coro())
        assert result == 42

    def test_run_async_exception_propagates(self):
        async def failing_coro():
            raise ValueError("boom")
        from tasks.pipeline_utils import _run_async
        with pytest.raises(ValueError, match="boom"):
            _run_async(failing_coro())


# =============================================================================
# _parse_json_field
# =============================================================================

class TestParseJsonField:

    def test_valid_json_string(self):
        from tasks.pipeline_utils import _parse_json_field
        assert _parse_json_field('[{"a": 1}]') == [{"a": 1}]

    def test_empty_string(self):
        from tasks.pipeline_utils import _parse_json_field
        assert _parse_json_field('') == []

    def test_invalid_json_string(self):
        from tasks.pipeline_utils import _parse_json_field
        assert _parse_json_field('not json') == []

    def test_list_input(self):
        from tasks.pipeline_utils import _parse_json_field
        assert _parse_json_field([1, 2]) == [1, 2]

    def test_none_input(self):
        from tasks.pipeline_utils import _parse_json_field
        assert _parse_json_field(None) == []


# =============================================================================
# _build_session_context
# =============================================================================

class TestBuildSessionContext:

    def test_empty_memories(self):
        from tasks.pipeline_utils import _build_session_context
        assert _build_session_context([]) == ""

    def test_with_memories(self):
        from tasks.pipeline_utils import _build_session_context
        m = MagicMock()
        m.content_type = "code"
        m.agent_role = "agent"
        m.summary = "wrote code"
        result = _build_session_context([m])
        assert "历史上下文" in result
        assert "wrote code" in result


# =============================================================================
# _is_balance_error
# =============================================================================

class TestIsBalanceError:

    def test_balance_error_keywords(self):
        from tasks.pipeline_utils import _is_balance_error
        assert _is_balance_error(Exception("insufficient_quota"))
        assert _is_balance_error(Exception("insufficient_balance"))
        assert _is_balance_error(Exception("insufficient balance"))
        assert _is_balance_error(Exception("余额不足"))
        assert _is_balance_error(Exception("billing limit"))
        assert _is_balance_error(Exception("quota exceeded"))
        assert _is_balance_error(Exception("payment required"))
        assert _is_balance_error(Exception("account balance"))
        assert _is_balance_error(Exception("402 Payment Required"))

    def test_not_balance_error(self):
        from tasks.pipeline_utils import _is_balance_error
        assert not _is_balance_error(Exception("rate limit"))
        assert not _is_balance_error(Exception("generic error"))


# =============================================================================
# _report_run_error
# =============================================================================

class TestReportRunError:

    @patch("tasks.pipeline_utils._run_async")
    @patch("tasks.pipeline_utils._is_balance_error", return_value=True)
    def test_balance_error_publishes_warning(self, mock_bal, mock_run_async):
        from tasks.pipeline_utils import _report_run_error
        mock_run_async.return_value = None
        _report_run_error("run-1", Exception("insufficient balance"))
        assert mock_run_async.call_count >= 3

    @patch("tasks.pipeline_utils._run_async")
    @patch("tasks.pipeline_utils._is_balance_error", return_value=False)
    def test_non_balance_error(self, mock_bal, mock_run_async):
        from tasks.pipeline_utils import _report_run_error
        mock_run_async.return_value = None
        _report_run_error("run-2", Exception("something else"))
        assert mock_run_async.call_count >= 2

    @patch("tasks.pipeline_utils._run_async", side_effect=Exception("publish fail"))
    def test_report_run_error_exception_is_swallowed(self, mock_run_async):
        from tasks.pipeline_utils import _report_run_error
        _report_run_error("run-3", Exception("test exc"))


# =============================================================================
# _try_mock_fallback
# =============================================================================

class TestTryMockFallback:

    @patch("tasks.pipeline_utils._run_async")
    @patch("tasks.pipeline_utils.run_mock", new_callable=AsyncMock)
    def test_success_with_session(self, mock_run_mock, mock_run_async):
        from tasks.pipeline_utils import _try_mock_fallback
        mock_output = MagicMock()
        mock_output.response = "mock response"
        mock_run_mock.return_value = mock_output

        # _run_async is called multiple times; return the right value each time
        call_count = [0]
        def side_effect(coro):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: run_mock — need to actually run it
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()
            return None
        mock_run_async.side_effect = side_effect

        result = _try_mock_fallback("req", "run-1", "sess-1", Exception("orig"))
        assert result is not None
        assert result["run_id"] == "run-1"
        assert result["fallback"] is True

    @patch("tasks.pipeline_utils._run_async")
    @patch("tasks.pipeline_utils.run_mock", new_callable=AsyncMock)
    def test_success_without_session(self, mock_run_mock, mock_run_async):
        from tasks.pipeline_utils import _try_mock_fallback
        mock_output = MagicMock()
        mock_output.response = "mock response"
        mock_run_mock.return_value = mock_output

        call_count = [0]
        def side_effect(coro):
            call_count[0] += 1
            if call_count[0] == 1:
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()
            return None
        mock_run_async.side_effect = side_effect

        result = _try_mock_fallback("req", "run-1", None, Exception("orig"))
        assert result is not None
        assert result["run_id"] == "run-1"

    @patch("tasks.pipeline_utils._run_async", side_effect=Exception("mock also failed"))
    @patch("tasks.pipeline_utils.run_mock", new_callable=AsyncMock)
    def test_mock_fallback_failure(self, mock_run_mock, mock_run_async):
        from tasks.pipeline_utils import _try_mock_fallback
        with pytest.raises(Exception, match="mock also failed"):
            _try_mock_fallback("req", "run-1", None, Exception("orig"))


# =============================================================================
# _discover_mcp_tools
# =============================================================================

class TestGetRagContext:

    async def test_get_rag_context_success(self):
        from tasks.pipeline_utils import _get_rag_context
        mock_cfg = AsyncMock(
            return_value={
                "api_key": "key-1",
                "base_url": "https://api.siliconflow.cn/v1",
                "model": "BAAI/bge-m3",
            }
        )
        mock_ensure = MagicMock()
        mock_retrieve = AsyncMock(return_value="rag result")
        mock_sources = AsyncMock(
            return_value=[{"asset_id": "a1", "asset_name": "手册", "text": "…", "similarity": 0.9}]
        )

        with patch("rag.rag_pipeline.ensure_embedding_provider", mock_ensure), \
             patch("rag.rag_pipeline.retrieve_context", mock_retrieve), \
             patch("rag.rag_pipeline.retrieve_sources", mock_sources), \
             patch("repository.keys.get_embedding_config", mock_cfg):
            context, sources = await _get_rag_context("query", "sess-1")

        assert context == "rag result"
        assert sources[0]["asset_id"] == "a1"
        mock_ensure.assert_called_once_with(
            "key-1", model="BAAI/bge-m3", base_url="https://api.siliconflow.cn/v1"
        )
        mock_sources.assert_awaited_once()
        mock_retrieve.assert_awaited_once()

    async def test_get_rag_context_no_key_returns_empty(self):
        from tasks.pipeline_utils import _get_rag_context
        mock_cfg = AsyncMock(return_value=None)
        with patch("repository.keys.get_embedding_config", mock_cfg):
            context, sources = await _get_rag_context("query", "sess-1")
        assert context == ""
        assert sources == []

    async def test_get_rag_context_exception_returns_empty(self):
        from tasks.pipeline_utils import _get_rag_context
        with patch("repository.keys.get_embedding_config", new_callable=AsyncMock, side_effect=Exception("fail")):
            context, sources = await _get_rag_context("query", "sess-1")
        assert context == ""
        assert sources == []

    async def test_get_rag_context_logs_retrieval(self):
        from tasks.pipeline_utils import _get_rag_context
        mock_cfg = AsyncMock(
            return_value={
                "api_key": "key-1",
                "base_url": "https://api.siliconflow.cn/v1",
                "model": "BAAI/bge-m3",
            }
        )
        mock_ensure = MagicMock()
        mock_retrieve = AsyncMock(return_value="rag result")
        mock_sources = AsyncMock(
            return_value=[{"asset_id": "a1", "asset_name": "手册", "text": "…", "similarity": 0.9}]
        )
        mock_log = AsyncMock()

        with patch("rag.rag_pipeline.ensure_embedding_provider", mock_ensure), \
             patch("rag.rag_pipeline.retrieve_context", mock_retrieve), \
             patch("rag.rag_pipeline.retrieve_sources", mock_sources), \
             patch("repository.keys.get_embedding_config", mock_cfg), \
             patch("repository.retrieval_logs.create_retrieval_log", mock_log):
            context, sources = await _get_rag_context("query", "sess-1", "u1")

        assert context == "rag result"
        mock_log.assert_awaited_once()
        kwargs = mock_log.call_args.kwargs
        assert kwargs["user_id"] == "u1"
        assert kwargs["session_id"] == "sess-1"
        assert kwargs["query"] == "query"
        assert kwargs["hit_count"] == 1
        assert kwargs["rerank"] is True
        assert kwargs["top_k"] == 3
        assert kwargs["latency_ms"] >= 0
        assert kwargs["sources"][0]["asset_id"] == "a1"

    async def test_get_rag_context_log_failure_does_not_break_chat(self):
        from tasks.pipeline_utils import _get_rag_context
        mock_cfg = AsyncMock(
            return_value={"api_key": "key-1", "base_url": "https://api.siliconflow.cn/v1", "model": "BAAI/bge-m3"}
        )
        mock_retrieve = AsyncMock(return_value="rag result")
        mock_sources = AsyncMock(return_value=[])
        mock_log = AsyncMock(side_effect=Exception("db down"))

        with patch("rag.rag_pipeline.ensure_embedding_provider", MagicMock()), \
             patch("rag.rag_pipeline.retrieve_context", mock_retrieve), \
             patch("rag.rag_pipeline.retrieve_sources", mock_sources), \
             patch("repository.keys.get_embedding_config", mock_cfg), \
             patch("repository.retrieval_logs.create_retrieval_log", mock_log):
            context, sources = await _get_rag_context("query", "sess-1")

        assert context == "rag result"
        assert sources == []


# =============================================================================
# _save_output_memories
# =============================================================================

class TestSaveOutputMemories:

    @patch("tasks.pipeline_utils.create_memory_entry", new_callable=AsyncMock)
    async def test_save_content_type(self, mock_create):
        from tasks.pipeline_utils import _save_output_memories
        await _save_output_memories("sess-1", "run-1", "写一篇小红书笔记", {})
        mock_create.assert_awaited_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["content_type"] == "content"

    @patch("tasks.pipeline_utils.create_memory_entry", new_callable=AsyncMock)
    async def test_save_exception_is_swallowed(self, mock_create):
        mock_create.side_effect = Exception("DB fail")
        from tasks.pipeline_utils import _save_output_memories
        await _save_output_memories("sess-1", "run-1", "response", {})

    @patch("tasks.pipeline_utils.create_memory_entry", new_callable=AsyncMock)
    async def test_save_summary_truncated(self, mock_create):
        from tasks.pipeline_utils import _save_output_memories
        long_response = "x" * 500
        await _save_output_memories("sess-1", "run-1", long_response, {})
        call_kwargs = mock_create.call_args[1]
        assert len(call_kwargs["summary"]) <= 200
        assert len(call_kwargs["details"]) <= 2000


# =============================================================================
# _run_shadow_retrieval (O4)
# =============================================================================

class TestShadowRetrieval:

    @pytest.mark.asyncio
    async def test_disabled_without_env(self, monkeypatch):
        monkeypatch.delenv("RAG_SHADOW_VARIANTS", raising=False)
        from tasks.pipeline_utils import _run_shadow_retrieval

        with patch("rag.rag_pipeline.retrieve_sources", new_callable=AsyncMock) as mock_retrieve, \
             patch("repository.shadow_retrieval.create_shadow_log", new_callable=AsyncMock) as mock_log:
            await _run_shadow_retrieval("q", "s1", "u1")

        mock_retrieve.assert_not_awaited()
        mock_log.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_replays_variant_when_configured(self, monkeypatch):
        monkeypatch.setenv("RAG_SHADOW_VARIANTS", "rerank:false,min_score:0.55")
        from tasks.pipeline_utils import _run_shadow_retrieval

        with patch("rag.rag_pipeline.retrieve_sources", new_callable=AsyncMock) as mock_retrieve, \
             patch("repository.shadow_retrieval.create_shadow_log", new_callable=AsyncMock) as mock_log:
            mock_retrieve.return_value = [{"asset_id": "a1", "text": "spec"}]
            await _run_shadow_retrieval("q", "s1", "u1")

        kwargs = mock_retrieve.call_args[1]
        assert kwargs["rerank"] is False
        assert kwargs["min_score"] == 0.55
        log_kwargs = mock_log.call_args[1]
        assert log_kwargs["variant"] == "rerank:false,min_score:0.55"
        assert log_kwargs["hit_count"] == 1
        assert log_kwargs["rerank"] is False

    @pytest.mark.asyncio
    async def test_ignores_unknown_variant_keys(self, monkeypatch):
        monkeypatch.setenv("RAG_SHADOW_VARIANTS", "bogus:1")
        from tasks.pipeline_utils import _run_shadow_retrieval

        with patch("rag.rag_pipeline.retrieve_sources", new_callable=AsyncMock) as mock_retrieve, \
             patch("repository.shadow_retrieval.create_shadow_log", new_callable=AsyncMock) as mock_log:
            await _run_shadow_retrieval("q", "s1", "u1")

        mock_retrieve.assert_not_awaited()
        mock_log.assert_not_awaited()
