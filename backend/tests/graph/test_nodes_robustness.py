"""Node robustness tests — exception paths of _tools_node / _image_node.

Covers the QA A7 change: UI event emissions are wrapped in
``contextlib.suppress`` so a failing stream callback must never break tool
execution, image generation, or answer construction. Also pins the
unknown-tool behavior (the tool registry was removed — any tool call
resolves to an "Unknown tool" result).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from graph.graph import SingleAgentGraph
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver


@pytest.fixture
def graph() -> SingleAgentGraph:
    """Create a SingleAgentGraph with MemorySaver and mocked ChatOpenAI."""
    with patch("graph.graph.ChatOpenAI") as MockLLM:
        MockLLM.return_value = MagicMock()
        g = SingleAgentGraph(
            model="test-model",
            api_key="test-key",
            base_url="http://localhost:9999",
            checkpointer=MemorySaver(),
        )
    return g


def _tool_call_message(tool_name: str = "search") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": tool_name, "args": {"q": "test"}, "id": "call-1"}],
    )


class TestToolsNodeRobustness:
    """_tools_node must survive stream-callback failures and unknown tools."""

    @pytest.mark.asyncio
    async def test_cb_failure_does_not_break_tools_node(self, graph: SingleAgentGraph):
        """UI 回调抛异常时，_tools_node 仍返回 Unknown tool 结果（A7 suppress 修复）。"""
        async def exploding_cb(event: dict) -> None:
            raise RuntimeError("cb boom")

        graph.set_stream_callback(exploding_cb)
        result = await graph._tools_node({"messages": [_tool_call_message()]})

        assert len(result["messages"]) == 1
        tm = result["messages"][0]
        assert isinstance(tm, ToolMessage)
        assert tm.content == "Unknown tool: search"
        assert tm.tool_call_id == "call-1"

    @pytest.mark.asyncio
    async def test_cb_failure_with_unknown_tool(self, graph: SingleAgentGraph):
        """回调抛异常 + 工具未注册，仍返回 Unknown tool 文本的 ToolMessage。"""
        async def exploding_cb(event: dict) -> None:
            raise RuntimeError("cb boom")

        graph.set_stream_callback(exploding_cb)
        result = await graph._tools_node({"messages": [_tool_call_message()]})

        tm = result["messages"][0]
        assert isinstance(tm, ToolMessage)
        assert tm.content == "Unknown tool: search"

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_unknown_message(self, graph: SingleAgentGraph):
        """未注册工具 → 不崩溃，返回 Unknown tool 提示。"""
        result = await graph._tools_node(
            {"messages": [_tool_call_message(tool_name="nonexistent")]}
        )

        tm = result["messages"][0]
        assert isinstance(tm, ToolMessage)
        assert tm.content == "Unknown tool: nonexistent"

    @pytest.mark.asyncio
    async def test_cb_failure_still_emits_node_end_and_returns(self, graph: SingleAgentGraph):
        """suppress 后 on_node_end 发射失败不阻断节点返回（含工具结果发射）。"""
        async def exploding_cb(event: dict) -> None:
            raise RuntimeError("cb boom")

        graph.set_stream_callback(exploding_cb)
        result = await graph._tools_node({"messages": [_tool_call_message()]})

        assert len(result["messages"]) == 1

    @pytest.mark.asyncio
    async def test_no_tool_calls_returns_empty(self, graph: SingleAgentGraph):
        """最后一条消息无 tool_calls → 空结果，不执行任何工具。"""
        result = await graph._tools_node(
            {"messages": [AIMessage(content="直接回答")]}
        )
        assert result == {}


class TestImageNodeRobustness:
    """_image_node must survive stream-callback failures and missing prompts."""

    @pytest.mark.asyncio
    async def test_cb_failure_still_returns_aimessage(self, graph: SingleAgentGraph):
        """回调三处发射（thinking/token/node_end）全部抛异常，仍返回图片 AIMessage。"""
        graph.image_model = True

        async def exploding_cb(event: dict) -> None:
            raise RuntimeError("cb boom")

        graph.set_stream_callback(exploding_cb)
        with patch("streaming.image_generation.generate_image", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "https://img.example/cat.png"
            result = await graph._agent_node(
                {"messages": [HumanMessage(content="一只橘猫")], "system_prompt": "", "session_context": ""}
            )

        mock_gen.assert_awaited_once()
        ai_msg = result["messages"][0]
        assert isinstance(ai_msg, AIMessage)
        assert ai_msg.content == "![生成的图片](https://img.example/cat.png)"

    @pytest.mark.asyncio
    async def test_empty_prompt_uses_default(self, graph: SingleAgentGraph):
        """无 human 消息 → 默认提示词"请生成一张图片"，不崩溃。"""
        graph.image_model = True
        with patch("streaming.image_generation.generate_image", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "https://img.example/x.png"
            await graph._agent_node({"messages": [], "system_prompt": "", "session_context": ""})

        args, _ = mock_gen.call_args
        assert args[1] == "请生成一张图片"
