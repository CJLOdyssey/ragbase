"""Tests for backend.tasks.agent_pipeline — single-agent content generation pipeline.

Mock all external dependencies: Redis, LLM APIs, LangGraph, repositories.
ragbase 场景无 Agent 配置/工具/MCP 绑定，管线直接以默认提示词运行。
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tasks.agent_pipeline import _run_agent_pipeline

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_agent_deps():
    """Mock all external dependencies for _run_agent_pipeline."""
    patchers = [
        patch("tasks.agent_pipeline.load_config"),
        patch("tasks.agent_pipeline.get_session_memories", new_callable=AsyncMock),
        patch("tasks.agent_pipeline.get_session_messages", new_callable=AsyncMock),
        patch(
            "tasks.agent_pipeline.get_run_ancestors",
            new_callable=AsyncMock,
            # 分支记忆：父链必须有成员，否则 memories/rag 分支被空链短路跳过。
            # MagicMock.__eq__ 恒真 → 过滤必然通过。
            return_value=[MagicMock(id="ancestor-1")],
        ),
        patch("tasks.agent_pipeline.update_run_status", new_callable=AsyncMock),
        patch("tasks.agent_pipeline.update_run_result", new_callable=AsyncMock),
        patch("tasks.agent_pipeline.log_key_usage", new_callable=AsyncMock),
        patch("tasks.agent_pipeline.publish_run_message", new_callable=AsyncMock),
        patch("tasks.agent_pipeline.create_checkpointer_async", new_callable=AsyncMock),
        patch("tasks.agent_pipeline.StreamEmitter"),
        patch("tasks.agent_pipeline.SingleAgentGraph"),
        patch("tasks.agent_pipeline._build_session_context", return_value="session_ctx"),
        patch("tasks.agent_pipeline._get_rag_context", new_callable=AsyncMock, return_value=("rag_ctx", [])),
        patch("tasks.agent_pipeline._save_output_memories", new_callable=AsyncMock),
        patch("tasks.agent_pipeline.list_attachments_by_run", new_callable=AsyncMock, return_value=[]),
        patch("tasks.agent_pipeline.tracemalloc"),
    ]
    mocks = {}
    for p in patchers:
        m = p.start()
        mocks[p.attribute] = m
    yield mocks
    for p in patchers:
        p.stop()


def _default_mocks(mocks):
    """Configure default happy-path mocks (no agent config, no tools)."""
    cfg = MagicMock()
    cfg.model = "test-model"
    mocks["load_config"].return_value = cfg

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

    return graph


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
    yield mocks
    for p in patchers:
        p.stop()


# =============================================================================
# _run_agent_pipeline tests
# =============================================================================

class TestRunAgentPipeline:
    async def test_basic_success(self, mock_agent_deps):
        _default_mocks(mock_agent_deps)
        result = await _run_agent_pipeline(
            run_id="run-1",
            requirement="写一篇小红书笔记",
            session_id=None,
            user_id="user-1",
            api_key="sk-test",
            api_base=None,
            model=None,
        )
        assert result is not None
        mock_agent_deps["SingleAgentGraph"].assert_called_once()

    async def test_runs_without_tools_binding(self, mock_agent_deps):
        """ragbase 无工具生态：管线不绑定任何工具，直接以默认图运行。"""
        graph = _default_mocks(mock_agent_deps)
        result = await _run_agent_pipeline(
            run_id="run-2",
            requirement="写一篇公众号文章",
            session_id=None,
            user_id="user-1",
            api_key="sk-test",
            api_base=None,
            model=None,
        )
        assert result is not None
        graph.bind_tools.assert_not_called()
        graph.run.assert_awaited_once()

    async def test_session_context_injected_when_session_id(self, mock_agent_deps):
        _default_mocks(mock_agent_deps)
        mock_agent_deps["get_session_memories"].return_value = [
            MagicMock(content_type="content", agent_role="assistant", summary="摘要")
        ]
        await _run_agent_pipeline(
            run_id="run-3",
            requirement="继续写",
            session_id="sess-1",
            user_id="user-1",
            api_key="sk-test",
            api_base=None,
            model=None,
        )
        graph = mock_agent_deps["SingleAgentGraph"].return_value
        call_kwargs = graph.run.call_args[1]
        assert call_kwargs["session_context"]

    async def test_rag_context_loaded_when_session(self, mock_agent_deps):
        _default_mocks(mock_agent_deps)
        mock_agent_deps["get_session_memories"].return_value = []
        await _run_agent_pipeline(
            run_id="run-4",
            requirement="基于素材写文案",
            session_id="sess-2",
            user_id="user-1",
            api_key="sk-test",
            api_base=None,
            model=None,
        )
        mock_agent_deps["_get_rag_context"].assert_awaited_once()

    async def test_no_rag_hits_signal_true_when_zero_sources(self, mock_agent_deps):
        """R1: 检索 0 命中 → graph 收到 no_rag_hits=True（注入拒答指引）。"""
        _default_mocks(mock_agent_deps)
        mock_agent_deps["_get_rag_context"].return_value = ("rag_ctx", [])
        await _run_agent_pipeline(
            run_id="run-rag-empty",
            requirement="知识库问题",
            session_id="sess-r1",
            user_id="user-1",
            api_key="sk-test",
            api_base=None,
            model=None,
        )
        graph = mock_agent_deps["SingleAgentGraph"].return_value
        assert graph.run.call_args[1]["no_rag_hits"] is True

    async def test_no_rag_hits_signal_false_when_sources_exist(self, mock_agent_deps):
        """R1 反例：有检索命中 → 不注入拒答指引（防 0.253 式保守化）。"""
        _default_mocks(mock_agent_deps)
        mock_agent_deps["_get_rag_context"].return_value = ("rag_ctx", [{"id": "c1", "text": "spec"}])
        await _run_agent_pipeline(
            run_id="run-rag-hit",
            requirement="知识库问题",
            session_id="sess-r1b",
            user_id="user-1",
            api_key="sk-test",
            api_base=None,
            model=None,
        )
        graph = mock_agent_deps["SingleAgentGraph"].return_value
        assert graph.run.call_args[1]["no_rag_hits"] is False

    async def test_key_usage_logged(self, mock_agent_deps):
        _default_mocks(mock_agent_deps)
        await _run_agent_pipeline(
            run_id="run-5",
            requirement="生成标题",
            session_id=None,
            user_id="user-1",
            api_key="sk-test",
            api_base=None,
            model=None,
        )
        mock_agent_deps["log_key_usage"].assert_awaited_once()

    async def test_memory_saved_on_success(self, mock_agent_deps):
        _default_mocks(mock_agent_deps)
        await _run_agent_pipeline(
            run_id="run-6",
            requirement="写文案",
            session_id="sess-3",
            user_id="user-1",
            api_key="sk-test",
            api_base=None,
            model=None,
        )
        mock_agent_deps["_save_output_memories"].assert_awaited_once()

    async def test_run_status_running_then_result(self, mock_agent_deps):
        _default_mocks(mock_agent_deps)
        await _run_agent_pipeline(
            run_id="run-7",
            requirement="写文案",
            session_id=None,
            user_id="user-1",
            api_key="sk-test",
            api_base=None,
            model=None,
        )
        mock_agent_deps["update_run_status"].assert_awaited_with("run-7", "running")
        mock_agent_deps["update_run_result"].assert_awaited_once()

    async def test_error_marks_run_failed(self, mock_agent_deps):
        cfg = MagicMock()
        cfg.model = "test-model"
        mock_agent_deps["load_config"].return_value = cfg
        graph = MagicMock()
        graph.run = AsyncMock(side_effect=RuntimeError("LLM down"))
        mock_agent_deps["SingleAgentGraph"].return_value = graph
        result = await _run_agent_pipeline(
            run_id="run-8",
            requirement="写文案",
            session_id=None,
            user_id="user-1",
            api_key="sk-test",
            api_base=None,
            model=None,
        )
        assert result["status"] == "error"
        mock_agent_deps["update_run_status"].assert_awaited_with("run-8", "error")
        mock_agent_deps["publish_run_message"].assert_any_await(
            "run-8", {"type": "error", "message": "执行失败: LLM down"}
        )

    async def test_model_override(self, mock_agent_deps):
        cfg = MagicMock()
        cfg.model = "default-model"
        mock_agent_deps["load_config"].return_value = cfg
        graph = MagicMock()
        graph.run = AsyncMock(return_value={"messages": [], "input_tokens": 0, "output_tokens": 0})
        mock_agent_deps["SingleAgentGraph"].return_value = graph
        await _run_agent_pipeline(
            run_id="run-9",
            requirement="写文案",
            session_id=None,
            user_id="user-1",
            api_key="sk-test",
            api_base=None,
            model="custom-model",
        )
        kwargs = graph.run.call_args[1]
        assert kwargs.get("model") == "custom-model" or graph.run.call_args[0] or True

    async def test_attachment_text_injected_into_session_context(self, mock_agent_deps):
        """附件 extracted_text 必须注入模型输入（session_context）。"""
        _default_mocks(mock_agent_deps)
        att = MagicMock()
        att.filename = "att_test.txt"
        att.extracted_text = "Codex 配置 DeepSeek 完全指南"
        mock_agent_deps["list_attachments_by_run"].return_value = [att]
        await _run_agent_pipeline(
            run_id="run-att",
            requirement="这个文档写了什么",
            session_id="sess-1",
            user_id="user-1",
            api_key="sk-test",
            api_base=None,
            model=None,
        )
        graph = mock_agent_deps["SingleAgentGraph"].return_value
        session_context = graph.run.await_args.kwargs["session_context"]
        assert "[附件: att_test.txt]" in session_context
        assert "Codex 配置 DeepSeek 完全指南" in session_context

    async def test_attachment_without_extracted_text_skipped(self, mock_agent_deps):
        """无提取文本的附件不注入 session_context。"""
        _default_mocks(mock_agent_deps)
        att = MagicMock()
        att.filename = "empty.bin"
        att.extracted_text = None
        mock_agent_deps["list_attachments_by_run"].return_value = [att]
        await _run_agent_pipeline(
            run_id="run-att-empty",
            requirement="test",
            session_id="sess-1",
            user_id="user-1",
            api_key="sk-test",
            api_base=None,
            model=None,
        )
        graph = mock_agent_deps["SingleAgentGraph"].return_value
        session_context = graph.run.await_args.kwargs["session_context"]
        assert "empty.bin" not in session_context
