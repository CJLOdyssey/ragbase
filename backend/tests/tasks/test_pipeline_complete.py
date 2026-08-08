"""Tests for backend.tasks — agent pipeline, completion pipeline, and helpers.

Mock all external dependencies: Celery, Redis, LLM APIs, LangGraph, repositories.
"""
from unittest.mock import AsyncMock, MagicMock, call, patch

import httpx
import pytest
from tasks.complete_pipeline import _complete_pipeline
from tasks.pipeline_utils import (
    _build_session_context,
    _is_balance_error,
    _parse_json_field,
)

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_agent_deps():
    """Mock all external dependencies for _run_agent_pipeline."""
    patchers = [
        patch("tasks.agent_pipeline.load_config"),
        patch("tasks.agent_pipeline.get_agent_config", new_callable=AsyncMock),
        patch("tasks.agent_pipeline.get_session_memories", new_callable=AsyncMock),
        patch("tasks.agent_pipeline.get_session_messages", new_callable=AsyncMock),
        patch("tasks.agent_pipeline.update_run_status", new_callable=AsyncMock),
        patch("tasks.agent_pipeline.update_run_result", new_callable=AsyncMock),
        patch("tasks.agent_pipeline.log_key_usage", new_callable=AsyncMock),
        patch("tasks.agent_pipeline.publish_run_message", new_callable=AsyncMock),
        patch("tasks.agent_pipeline.create_checkpointer_async", new_callable=AsyncMock),
        patch("tasks.agent_pipeline.StreamEmitter"),
        patch("tasks.agent_pipeline.SingleAgentGraph"),
        patch("tasks.agent_pipeline._build_session_context", return_value="session_ctx"),
        patch("tasks.agent_pipeline._get_rag_context", new_callable=AsyncMock, return_value="rag_ctx"),
        patch("tasks.agent_pipeline._save_output_memories", new_callable=AsyncMock),
    ]
    mocks = {}
    for p in patchers:
        m = p.start()
        mocks[p.attribute] = m
    yield mocks
    for p in patchers:
        p.stop()


def _default_agent_mocks(mocks, agent_id="agent-1"):
    cfg = MagicMock()
    cfg.model = "test-model"
    mocks["load_config"].return_value = cfg

    ac = MagicMock()
    ac.system_prompt = "You are a test agent"
    ac.output_constraints = ""
    ac.model = None
    ac.tools = '[]'
    ac.mcp = '[]'
    ac.skills = '[]'
    mocks["get_agent_config"].return_value = ac

    graph = MagicMock()
    graph.run = AsyncMock()
    graph.run.return_value = {
        "messages": [MagicMock(content="Hello world!", tool_calls=None)],
        "input_tokens": 100,
        "output_tokens": 50,
        "model": "test-model",
    }
    graph.bind_tools = MagicMock()
    mocks["SingleAgentGraph"].return_value = graph

    return ac, graph


@pytest.fixture
def mock_complete_deps():
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


# =============================================================================
# _run_agent_pipeline tests
# =============================================================================


class TestCompletePipeline:

    async def test_success_no_thinking(self, mock_complete_deps):
        content = "Hello"
        api_key = "sk-test"
        mock_complete_deps["stream_prefix_completion"].return_value = (" world!", [])

        result = await _complete_pipeline(
            content=content,
            run_id="run-c1",
            api_key=api_key,
            api_base=None,
            model=None,
            thinking=None,
        )

        mock_complete_deps["update_run_status"].assert_awaited_with("run-c1", "running")

        args, _ = mock_complete_deps["stream_prefix_completion"].await_args
        body = args[2]
        assert body["model"] == "test-model"
        assert "Continue the following answer draft naturally" in body["messages"][0]["content"]
        assert "Hello" in body["messages"][0]["content"]

        mock_complete_deps["update_run_result"].assert_awaited_with(
            "run-c1",
            pm_document="",
            code=content + " world!",
            review="",
            approved=False,
            status="completed",
        )
        mock_complete_deps["publish_run_message"].assert_awaited_with(
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

    async def test_success_with_thinking(self, mock_complete_deps):
        content = "Continue this"
        api_key = "sk-test"
        api_base = "https://api.deepseek.com"
        mock_complete_deps["stream_prefix_completion"].return_value = (" continued text.", ["thinking..."])

        result = await _complete_pipeline(
            content=content,
            run_id="run-c2",
            api_key=api_key,
            api_base=api_base,
            model="deepseek-v4-flash",
            thinking="previous reasoning",
            question="原问题",
        )

        args, _ = mock_complete_deps["stream_prefix_completion"].await_args
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
        assert thinking_call in mock_complete_deps["publish_run_message"].await_args_list

        mock_complete_deps["update_run_result"].assert_awaited_with(
            "run-c2",
            pm_document="",
            code=content + " continued text.",
            review="",
            approved=False,
            status="completed",
        )
        assert result is None

    async def test_http_error(self, mock_complete_deps):
        mock_complete_deps["stream_prefix_completion"].side_effect = httpx.HTTPStatusError(
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

        mock_complete_deps["update_run_status"].assert_awaited_with("run-c3", "error")
        mock_complete_deps["publish_run_message"].assert_awaited_with(
            "run-c3",
            {"type": "error", "detail": "LLM API 错误: 402 Payment Required"},
        )
        assert result is None

    async def test_general_error_in_stream(self, mock_complete_deps):
        mock_complete_deps["stream_prefix_completion"].side_effect = RuntimeError("Network timeout")

        result = await _complete_pipeline(
            content="test",
            run_id="run-c4",
            api_key="sk-test",
            api_base=None,
            model=None,
            thinking=None,
        )

        mock_complete_deps["update_run_status"].assert_awaited_with("run-c4", "error")
        mock_complete_deps["publish_run_message"].assert_awaited_with(
            "run-c4",
            {"type": "error", "detail": "续写失败: Network timeout"},
        )
        assert result is None

    async def test_save_error(self, mock_complete_deps):
        mock_complete_deps["stream_prefix_completion"].return_value = ("output", [])
        mock_complete_deps["update_run_result"].side_effect = RuntimeError("DB write failed")

        result = await _complete_pipeline(
            content="test",
            run_id="run-c5",
            api_key="sk-test",
            api_base=None,
            model=None,
            thinking=None,
        )

        mock_complete_deps["update_run_status"].assert_awaited_with("run-c5", "error")
        mock_complete_deps["publish_run_message"].assert_awaited_with(
            "run-c5",
            {"type": "error", "detail": "保存失败: DB write failed"},
        )
        assert result is None

    async def test_custom_model_and_base(self, mock_complete_deps):
        content = "test"
        api_key = "sk-custom"
        api_base = "https://custom.api.com/v1"
        model = "custom-model"
        mock_complete_deps["stream_prefix_completion"].return_value = (" output", [])

        await _complete_pipeline(
            content=content,
            run_id="run-c6",
            api_key=api_key,
            api_base=api_base,
            model=model,
            thinking=None,
        )

        args, _ = mock_complete_deps["stream_prefix_completion"].await_args
        url = args[0]
        body = args[2]
        assert "custom.api.com" in url
        assert body["model"] == "custom-model"

    async def test_with_thinking_non_deepseek_api(self, mock_complete_deps):
        mock_complete_deps["stream_prefix_completion"].return_value = (" out", [])
        await _complete_pipeline(
            content="test",
            run_id="run-c7",
            api_key="sk-test",
            api_base="https://custom.api.com/v1",
            model="custom-model",
            thinking="prev thought",
        )

        args, _ = mock_complete_deps["stream_prefix_completion"].await_args
        body = args[2]
        assert body.get("thinking", {}).get("type") != "enabled"


# =============================================================================
# Helpers unit tests
# =============================================================================

class TestHelpers:

    def test_build_session_context(self):
        m1 = MagicMock()
        m1.content_type = "code"
        m1.agent_role = "agent"
        m1.summary = "wrote hello world"
        m2 = MagicMock()
        m2.content_type = "review"
        m2.agent_role = "agent"
        m2.summary = "checked style"

        ctx = _build_session_context([m1, m2])
        assert "历史上下文" in ctx
        assert "wrote hello world" in ctx
        assert "checked style" in ctx

    def test_build_session_context_empty(self):
        assert _build_session_context([]) == ""

    def test_parse_json_field_string(self):
        assert _parse_json_field('[{"a": 1}]') == [{"a": 1}]
        assert _parse_json_field('') == []
        assert _parse_json_field('invalid') == []

    def test_parse_json_field_list(self):
        assert _parse_json_field([1, 2, 3]) == [1, 2, 3]
        assert _parse_json_field(None) == []

    def test_is_balance_error(self):
        assert _is_balance_error(Exception("insufficient_quota"))
        assert _is_balance_error(Exception("余额不足"))
        assert _is_balance_error(Exception("402 Payment Required"))
        assert not _is_balance_error(Exception("rate limit exceeded"))
        assert not _is_balance_error(Exception("generic error"))
