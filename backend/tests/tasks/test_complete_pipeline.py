"""Tests for backend.tasks.complete_pipeline — continuation ("继续生成") flow.

Mock all external dependencies: Redis, httpx, LLM API.
"""
from unittest.mock import AsyncMock, MagicMock, call, patch

import httpx
import pytest
from tasks.complete_pipeline import _complete_pipeline


@pytest.fixture
def mock_deps():
    """Mock all external dependencies for _complete_pipeline."""
    patchers = [
        patch("tasks.complete_pipeline.load_config"),
        patch("tasks.complete_pipeline.update_run_status", new_callable=AsyncMock),
        patch("tasks.complete_pipeline.update_run_result", new_callable=AsyncMock),
        patch("tasks.complete_pipeline.publish_run_message", new_callable=AsyncMock),
        patch("tasks.complete_pipeline.stream_prefix_completion", new_callable=AsyncMock),
    ]
    mocks = {}
    for p in patchers:
        m = p.start()
        mocks[p.attribute] = m
    cfg = MagicMock()
    cfg.model = "test-model"
    mocks["load_config"].return_value = cfg
    yield mocks
    for p in patchers:
        p.stop()


class TestCompletePipeline:

    async def test_success_no_thinking(self, mock_deps):
        content = "Hello"
        api_key = "sk-test"
        mock_deps["stream_prefix_completion"].return_value = (" world!", [])

        result = await _complete_pipeline(
            content=content,
            run_id="run-c1",
            api_key=api_key,
            api_base=None,
            model=None,
            thinking=None,
        )

        mock_deps["update_run_status"].assert_awaited_with("run-c1", "running")

        args, _ = mock_deps["stream_prefix_completion"].await_args
        body = args[2]
        assert body["model"] == "test-model"
        assert "Continue the following answer draft naturally" in body["messages"][0]["content"]
        assert "Hello" in body["messages"][0]["content"]
        assert body.get("stream") is True

        mock_deps["update_run_result"].assert_awaited_with(
            "run-c1",
            pm_document="",
            code=content + " world!",
            review="",
            approved=False,
            status="completed",
        )
        mock_deps["publish_run_message"].assert_awaited_with(
            "run-c1",
            {
                "type": "result",
                "status": "completed",
                "code": content + " world!",
                "pm_document": "",
                "review": "",
                "approved": False,
            },
        )
        assert result is None

    async def test_success_with_thinking(self, mock_deps):
        content = "Continue this"
        api_key = "sk-test"
        api_base = "https://api.deepseek.com"
        mock_deps["stream_prefix_completion"].return_value = (" continued text.", ["thinking..."])

        result = await _complete_pipeline(
            content=content,
            run_id="run-c2",
            api_key=api_key,
            api_base=api_base,
            model="deepseek-v4-flash",
            thinking="previous reasoning",
            question="原问题",
        )

        args, _ = mock_deps["stream_prefix_completion"].await_args
        url = args[0]
        body = args[2]
        assert "/beta/chat/completions" in url
        assert body["model"] == "deepseek-v4-flash"
        assert body["messages"][0] == {"role": "user", "content": "原问题"}
        assert body["messages"][1]["role"] == "assistant"
        assert body["messages"][1]["content"] == content
        assert body["messages"][1]["prefix"] is True
        assert body.get("thinking") == {"type": "enabled"}

        thinking_call = call(
            "run-c2",
            {
                "type": "thinking_done",
                "agent_name": "Agent",
                "thinking": "previous reasoningthinking...",
            },
        )
        assert thinking_call in mock_deps["publish_run_message"].await_args_list

        mock_deps["update_run_result"].assert_awaited_with(
            "run-c2",
            pm_document="",
            code=content + " continued text.",
            review="",
            approved=False,
            status="completed",
        )
        assert result is None

    async def test_http_error(self, mock_deps):
        mock_deps["stream_prefix_completion"].side_effect = httpx.HTTPStatusError(
            "402 Payment Required",
            request=MagicMock(),
            response=MagicMock(status_code=402),
        )

        result = await _complete_pipeline(
            content="test",
            run_id="run-c3",
            api_key="sk-test",
            api_base=None,
            model=None,
            thinking=None,
        )

        mock_deps["update_run_status"].assert_awaited_with("run-c3", "error")
        mock_deps["publish_run_message"].assert_awaited_with(
            "run-c3",
            {"type": "error", "detail": "LLM API 错误: 402 Payment Required"},
        )
        assert result is None

    async def test_general_error_in_stream(self, mock_deps):
        mock_deps["stream_prefix_completion"].side_effect = RuntimeError("Network timeout")

        result = await _complete_pipeline(
            content="test",
            run_id="run-c4",
            api_key="sk-test",
            api_base=None,
            model=None,
            thinking=None,
        )

        mock_deps["update_run_status"].assert_awaited_with("run-c4", "error")
        mock_deps["publish_run_message"].assert_awaited_with(
            "run-c4",
            {"type": "error", "detail": "续写失败: Network timeout"},
        )
        assert result is None

    async def test_save_error(self, mock_deps):
        mock_deps["stream_prefix_completion"].return_value = ("output", [])
        mock_deps["update_run_result"].side_effect = RuntimeError("DB write failed")

        result = await _complete_pipeline(
            content="test",
            run_id="run-c5",
            api_key="sk-test",
            api_base=None,
            model=None,
            thinking=None,
        )

        mock_deps["update_run_status"].assert_awaited_with("run-c5", "error")
        mock_deps["publish_run_message"].assert_awaited_with(
            "run-c5",
            {"type": "error", "detail": "保存失败: DB write failed"},
        )
        assert result is None

    async def test_custom_model_and_base(self, mock_deps):
        content = "test"
        api_key = "sk-custom"
        api_base = "https://custom.api.com/v1"
        model = "custom-model"
        mock_deps["stream_prefix_completion"].return_value = (" output", [])

        await _complete_pipeline(
            content=content,
            run_id="run-c6",
            api_key=api_key,
            api_base=api_base,
            model=model,
            thinking=None,
        )

        args, _ = mock_deps["stream_prefix_completion"].await_args
        url = args[0]
        body = args[2]
        assert "custom.api.com" in url
        assert body["model"] == "custom-model"

    async def test_proc_read_error_does_not_crash(self, mock_deps):
        """Lines 38-39, 138-139: /proc read failure is silently ignored."""
        mock_deps["stream_prefix_completion"].return_value = (" output", [])

        with patch("tasks.complete_pipeline.os") as mock_os:
            mock_os.getpid.return_value = 999999
            mock_os.open.side_effect = OSError("no such proc")
            result = await _complete_pipeline(
                content="test",
                run_id="run-proc-err",
                api_key="sk-test",
                api_base=None,
                model=None,
                thinking=None,
            )

        assert result is None
        mock_deps["update_run_result"].assert_awaited()

    async def test_proc_read_error_in_thinking_path(self, mock_deps):
        """Lines 38-39, 138-139: /proc read failure with thinking enabled."""
        mock_deps["stream_prefix_completion"].return_value = (" result", ["thinking"])

        with patch("tasks.complete_pipeline.os") as mock_os:
            mock_os.getpid.return_value = 999999
            mock_os.open.side_effect = OSError("no such proc")
            result = await _complete_pipeline(
                content="test",
                run_id="run-proc-think",
                api_key="sk-test",
                api_base="https://api.deepseek.com",
                model="deepseek-v4",
                thinking="prev thought",
            )

        assert result is None

    async def test_tracemalloc_starts_when_not_tracing(self, mock_deps):
        """Line 41: tracemalloc.start() called when MEM_TRACE on and not already tracing."""
        mock_deps["stream_prefix_completion"].return_value = (" output", [])

        with patch("tasks.complete_pipeline.tracemalloc") as mock_tm, patch.dict(
            "os.environ", {"MEM_TRACE": "1"}
        ):
            mock_tm.is_tracing.return_value = False
            await _complete_pipeline(
                content="test",
                run_id="run-tracemalloc",
                api_key="sk-test",
                api_base=None,
                model=None,
                thinking=None,
            )
            mock_tm.start.assert_called_once_with(25)
