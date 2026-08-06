"""Tests for SingleAgentGraph execution path in backend/graph/graph.py.

Mocks the LLM and streaming layer to exercise _agent_node, _tools_node,
_should_continue, run, arun, and set_stream_callback without real HTTP calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END

from graph.graph import SingleAgentGraph


# ── Fixtures ──────────────────────────────────────────────────────────────────


class _FakeToolExecutor:
    """Minimal tool executor that satisfies the ToolExecutor protocol."""

    def __init__(self, result: str = "ok"):
        self.name = ""
        self.description = ""
        self._result = result
        self._side_effect: BaseException | None = None

    def set_side_effect(self, exc: BaseException) -> None:
        self._side_effect = exc

    async def invoke(self, args: dict) -> str:
        if self._side_effect:
            raise self._side_effect
        return self._result

    def set_llm(self, llm: object) -> None:
        pass

    def set_run_id(self, run_id: str) -> None:
        pass


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


@pytest.fixture
def graph_with_tools(graph: SingleAgentGraph) -> SingleAgentGraph:
    """Graph with two fake tools bound."""
    from services.tool_config import ToolConfig

    tool1 = ToolConfig(
        name="search",
        description="Search the web",
        parameters={"type": "object", "properties": {"query": {"type": "string"}}},
    )
    tool2 = ToolConfig(
        name="calculate",
        description="Calculate expression",
        parameters={"type": "object", "properties": {"expr": {"type": "string"}}},
    )
    graph.bind_tools([tool1, tool2])
    return graph


# ── _should_continue tests ────────────────────────────────────────────────────


class TestShouldContinue:
    def test_returns_tools_when_last_message_has_tool_calls(self, graph: SingleAgentGraph):
        last_msg = AIMessage(
            content="",
            tool_calls=[{"name": "search", "args": {"query": "test"}, "id": "tc_1"}],
        )
        state = {"messages": [HumanMessage(content="hi"), last_msg]}
        assert graph._should_continue(state) == "tools"

    def test_returns_end_when_no_tool_calls(self, graph: SingleAgentGraph):
        last_msg = AIMessage(content="Here is the answer.")
        state = {"messages": [HumanMessage(content="hi"), last_msg]}
        assert graph._should_continue(state) == END

    def test_returns_end_when_messages_empty(self, graph: SingleAgentGraph):
        assert graph._should_continue({"messages": []}) == END

    def test_returns_end_when_last_message_not_ai(self, graph: SingleAgentGraph):
        state = {"messages": [HumanMessage(content="hello")]}
        assert graph._should_continue(state) == END

    def test_returns_tools_only_for_last_message(self, graph: SingleAgentGraph):
        """Tool calls on an earlier message should not trigger continuation."""
        ai_with_tools = AIMessage(
            content="",
            tool_calls=[{"name": "search", "args": {}, "id": "tc_1"}],
        )
        ai_final = AIMessage(content="Done.")
        state = {"messages": [ai_with_tools, ai_final]}
        assert graph._should_continue(state) == END


# ── _agent_node tests ─────────────────────────────────────────────────────────


class TestAgentNode:
    @pytest.mark.asyncio
    async def test_returns_ai_message_with_content(self, graph: SingleAgentGraph):
        fake_content = "Hello from the LLM"
        fake_thinking = ""
        fake_tool_calls: list[dict] = []
        with patch.object(graph, "_raw_llm_stream", new_callable=AsyncMock) as mock_stream:
            mock_stream.return_value = (fake_content, fake_thinking, fake_tool_calls)
            state = {"messages": [HumanMessage(content="hi")]}
            result = await graph._agent_node(state)

        assert "messages" in result
        msgs = result["messages"]
        assert len(msgs) == 1
        assert isinstance(msgs[0], AIMessage)
        assert msgs[0].content == fake_content

    @pytest.mark.asyncio
    async def test_includes_system_prompt_when_provided(self, graph: SingleAgentGraph):
        with patch.object(graph, "_raw_llm_stream", new_callable=AsyncMock) as mock_stream:
            mock_stream.return_value = ("ok", "", [])
            state = {
                "messages": [HumanMessage(content="hi")],
                "system_prompt": "You are helpful.",
                "session_context": "",
            }
            await graph._agent_node(state)

        calls = mock_stream.call_args
        passed_messages = calls[0][0]
        system_msgs = [m for m in passed_messages if m.type == "system"]
        assert len(system_msgs) >= 1
        assert any("You are helpful." in m.content for m in system_msgs)

    @pytest.mark.asyncio
    async def test_includes_session_context_when_provided(self, graph: SingleAgentGraph):
        with patch.object(graph, "_raw_llm_stream", new_callable=AsyncMock) as mock_stream:
            mock_stream.return_value = ("ok", "", [])
            state = {
                "messages": [HumanMessage(content="hi")],
                "system_prompt": "",
                "session_context": "Project: AgentStudio",
            }
            await graph._agent_node(state)

        passed_messages = mock_stream.call_args[0][0]
        system_msgs = [m for m in passed_messages if m.type == "system"]
        assert any("AgentStudio" in m.content for m in system_msgs)

    @pytest.mark.asyncio
    async def test_tool_calls_attached_to_ai_message(self, graph: SingleAgentGraph):
        tool_calls = [{"name": "search", "args": {"query": "x"}, "id": "tc_1"}]
        with patch.object(graph, "_raw_llm_stream", new_callable=AsyncMock) as mock_stream:
            mock_stream.return_value = ("", "", tool_calls)
            state = {"messages": [HumanMessage(content="search")]}
            result = await graph._agent_node(state)

        ai_msg = result["messages"][0]
        # LangChain adds 'type' field to tool_calls, so check key fields
        assert len(ai_msg.tool_calls) == 1
        assert ai_msg.tool_calls[0]["name"] == "search"
        assert ai_msg.tool_calls[0]["args"] == {"query": "x"}
        assert ai_msg.tool_calls[0]["id"] == "tc_1"

    @pytest.mark.asyncio
    async def test_thinking_stored_in_additional_kwargs(self, graph: SingleAgentGraph):
        with patch.object(graph, "_raw_llm_stream", new_callable=AsyncMock) as mock_stream:
            mock_stream.return_value = ("answer", "deep thinking here", [])
            state = {"messages": [HumanMessage(content="why?")]}
            result = await graph._agent_node(state)

        ai_msg = result["messages"][0]
        assert ai_msg.additional_kwargs.get("thinking") == "deep thinking here"

    @pytest.mark.asyncio
    async def test_stream_callback_invoked_for_thinking_nodes(self, graph: SingleAgentGraph):
        cb = AsyncMock()
        graph.set_stream_callback(cb)
        tool_calls = [{"name": "calc", "args": {"expr": "1+1"}, "id": "tc_1"}]
        with patch.object(graph, "_raw_llm_stream", new_callable=AsyncMock) as mock_stream:
            mock_stream.return_value = ("", "thinking content", tool_calls)
            state = {"messages": [HumanMessage(content="calc")]}
            await graph._agent_node(state)

        thinking_call = cb.call_args_list[0]
        assert thinking_call[0][0]["event"] == "on_thinking_nodes"
        nodes = thinking_call[0][0]["data"]["nodes"]
        assert any(n["type"] == "thought" for n in nodes)

    @pytest.mark.asyncio
    async def test_stream_callback_invoked_on_node_end(self, graph: SingleAgentGraph):
        cb = AsyncMock()
        graph.set_stream_callback(cb)
        with patch.object(graph, "_raw_llm_stream", new_callable=AsyncMock) as mock_stream:
            mock_stream.return_value = ("done", "", [])
            state = {"messages": [HumanMessage(content="hi")]}
            await graph._agent_node(state)

        events = [call[0][0]["event"] for call in cb.call_args_list]
        assert "on_node_end" in events


# ── _tools_node tests ─────────────────────────────────────────────────────────


class TestToolsNode:
    @pytest.mark.asyncio
    async def test_executes_tool_calls(self, graph_with_tools: SingleAgentGraph):
        g = graph_with_tools
        g._tool_map["search"] = _FakeToolExecutor(result="search result")

        ai_msg = AIMessage(
            content="",
            tool_calls=[{"name": "search", "args": {"query": "test"}, "id": "tc_1"}],
        )
        state = {"messages": [HumanMessage(content="search"), ai_msg]}
        result = await g._tools_node(state)

        assert "messages" in result
        tool_msgs = result["messages"]
        assert len(tool_msgs) == 1
        assert isinstance(tool_msgs[0], ToolMessage)
        assert tool_msgs[0].content == "search result"

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_tool_calls(self, graph: SingleAgentGraph):
        ai_msg = AIMessage(content="No tools needed.")
        state = {"messages": [HumanMessage(content="hi"), ai_msg]}
        result = await graph._tools_node(state)
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_messages(self, graph: SingleAgentGraph):
        result = await graph._tools_node({"messages": []})
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_when_last_msg_not_ai(self, graph: SingleAgentGraph):
        state = {"messages": [HumanMessage(content="hi")]}
        result = await graph._tools_node(state)
        assert result == {}

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error_message(self, graph: SingleAgentGraph):
        ai_msg = AIMessage(
            content="",
            tool_calls=[{"name": "nonexistent", "args": {}, "id": "tc_1"}],
        )
        state = {"messages": [HumanMessage(content="use nonexistent"), ai_msg]}
        result = await graph._tools_node(state)

        tool_msg = result["messages"][0]
        assert "Unknown tool" in tool_msg.content

    @pytest.mark.asyncio
    async def test_tool_exception_returns_error(self, graph: SingleAgentGraph):
        g = graph
        executor = _FakeToolExecutor(result="never reached")
        executor.set_side_effect(RuntimeError("boom"))
        g._tool_map["fail_tool"] = executor

        ai_msg = AIMessage(
            content="",
            tool_calls=[{"name": "fail_tool", "args": {}, "id": "tc_1"}],
        )
        state = {"messages": [HumanMessage(content="fail"), ai_msg]}
        result = await g._tools_node(state)

        assert "Error: boom" in result["messages"][0].content

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_all_executed(self, graph_with_tools: SingleAgentGraph):
        g = graph_with_tools
        g._tool_map["search"] = _FakeToolExecutor(result="search result")
        g._tool_map["calculate"] = _FakeToolExecutor(result="42")

        ai_msg = AIMessage(
            content="",
            tool_calls=[
                {"name": "search", "args": {"query": "a"}, "id": "tc_1"},
                {"name": "calculate", "args": {"expr": "2*21"}, "id": "tc_2"},
            ],
        )
        state = {"messages": [HumanMessage(content="both"), ai_msg]}
        result = await g._tools_node(state)

        assert len(result["messages"]) == 2
        assert result["messages"][0].content == "search result"
        assert result["messages"][1].content == "42"

    @pytest.mark.asyncio
    async def test_stream_callback_on_tool_result(self, graph: SingleAgentGraph):
        cb = AsyncMock()
        graph.set_stream_callback(cb)
        graph._tool_map["echo"] = _FakeToolExecutor(result="hello echo")

        ai_msg = AIMessage(
            content="",
            tool_calls=[{"name": "echo", "args": {"text": "hi"}, "id": "tc_1"}],
        )
        state = {"messages": [HumanMessage(content="echo"), ai_msg]}
        await graph._tools_node(state)

        events = [call[0][0]["event"] for call in cb.call_args_list]
        # Tool results are streamed into the thinking chain as on_custom_thinking
        # with a "[result] <tool> → ..." prefix.
        assert "on_custom_thinking" in events
        result_thoughts = [
            c[0][0]["data"]["content"]
            for c in cb.call_args_list
            if c[0][0]["event"] == "on_custom_thinking"
        ]
        assert any(t.startswith("[result] echo →") for t in result_thoughts)


# ── set_stream_callback tests ─────────────────────────────────────────────────


class TestSetStreamCallback:
    def test_stores_callback(self, graph: SingleAgentGraph):
        cb = MagicMock()
        graph.set_stream_callback(cb)
        assert graph._stream_cb is cb

    def test_none_callback_clears_previous(self, graph: SingleAgentGraph):
        graph.set_stream_callback(MagicMock())
        graph.set_stream_callback(None)
        assert graph._stream_cb is None


# ── run / arun tests ──────────────────────────────────────────────────────────


class TestRunAndArun:
    @pytest.mark.asyncio
    async def test_run_returns_messages_and_usage(self, graph: SingleAgentGraph):
        fake_ai = AIMessage(content="final answer")
        fake_result = {"messages": [HumanMessage(content="q"), fake_ai]}
        graph._graph = MagicMock()
        graph._graph.ainvoke = AsyncMock(return_value=fake_result)

        result = await graph.run(
            requirement="What is 2+2?",
            system_prompt="You are a math tutor.",
            session_context="",
            thread_id="t1",
        )

        assert result["messages"] == fake_result["messages"]
        assert result["model"] == "test-model"
        assert "input_tokens" in result
        assert "output_tokens" in result

    @pytest.mark.asyncio
    async def test_run_passes_chat_history(self, graph: SingleAgentGraph):
        history = [HumanMessage(content="previous"), AIMessage(content="prior answer")]
        fake_ai = AIMessage(content="next")
        fake_result = {"messages": history + [HumanMessage(content="follow up"), fake_ai]}
        graph._graph = MagicMock()
        graph._graph.ainvoke = AsyncMock(return_value=fake_result)

        result = await graph.run(
            requirement="follow up",
            chat_history=history,
            thread_id="t2",
        )

        invoke_call = graph._graph.ainvoke
        initial_state = invoke_call.call_args[0][0]
        msgs = initial_state["messages"]
        # Initial state: chat_history (2) + new HumanMessage (1) = 3
        assert len(msgs) == 3
        assert msgs[0].content == "previous"
        assert msgs[1].content == "prior answer"
        assert msgs[2].content == "follow up"

        # Final result includes the AI response
        assert result["messages"][-1].content == "next"

    @pytest.mark.asyncio
    async def test_run_generates_thread_id_when_empty(self, graph: SingleAgentGraph):
        graph._graph = MagicMock()
        graph._graph.ainvoke = AsyncMock(return_value={"messages": [AIMessage(content="hi")]})

        await graph.run(requirement="hi")

        config = graph._graph.ainvoke.call_args[0][1]
        thread_id = config["configurable"]["thread_id"]
        assert thread_id  # non-empty

    @pytest.mark.asyncio
    async def test_arun_returns_last_message_content(self, graph: SingleAgentGraph):
        fake_result = {"messages": [HumanMessage(content="q"), AIMessage(content="the answer")]}
        graph._graph = MagicMock()
        graph._graph.ainvoke = AsyncMock(return_value=fake_result)

        text = await graph.arun("What is the meaning of life?")

        assert text == "the answer"

    @pytest.mark.asyncio
    async def test_arun_returns_empty_when_no_messages(self, graph: SingleAgentGraph):
        graph._graph = MagicMock()
        graph._graph.ainvoke = AsyncMock(return_value={"messages": []})

        text = await graph.arun("hello")
        assert text == ""

    @pytest.mark.asyncio
    async def test_run_uses_last_usage_for_tokens(self, graph: SingleAgentGraph):
        graph._last_usage = {"input_tokens": 100, "output_tokens": 50}
        graph._graph = MagicMock()
        graph._graph.ainvoke = AsyncMock(return_value={"messages": [AIMessage(content="ok")]})

        result = await graph.run(requirement="ok")

        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 50

    @pytest.mark.asyncio
    async def test_run_uses_default_tokens_when_empty(self, graph: SingleAgentGraph):
        graph._last_usage = {}
        graph._graph = MagicMock()
        graph._graph.ainvoke = AsyncMock(return_value={"messages": [AIMessage(content="ok")]})

        result = await graph.run(requirement="ok")

        assert result["input_tokens"] == 0
        assert result["output_tokens"] == 0
