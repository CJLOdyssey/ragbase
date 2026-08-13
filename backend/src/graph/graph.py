"""LangGraph-based single Agent engine with DeepSeek thinking support.

Architecture:
  START -> agent -> [has tool_calls?] --yes--> tools -> agent
                    `-- no ---> END
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, cast

from core._interfaces import ToolDescriptor, ToolExecutor
from langchain_core.messages import HumanMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from graph.graph_state import AgentState  # noqa: F401  # re-exported for backward compat
from graph.helpers import (
    CONTEXT_GUARD_PROMPT,  # noqa: F401  # re-exported for backward compat
    _emit_balance_warning,  # noqa: F401  # re-exported for backward compat
    _InlineToolExecutor,
    _is_balance_error,  # noqa: F401  # re-exported for backward compat
    _load_context_guard_template,  # noqa: F401  # re-exported for backward compat
)
from graph.nodes import GraphNodesMixin


class SingleAgentGraph(GraphNodesMixin):
    """Builds and runs a ReAct agent graph with DeepSeek thinking support."""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 16384,
        checkpointer: BaseCheckpointSaver[Any] | None = None,
        image_model: bool = False,
    ):
        """Initialize the ReAct agent graph with LLM and checkpointer."""
        self.model = model
        self.image_model = image_model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._run_id = None
        self._last_usage: dict[str, Any] = {}

        llm_kwargs: dict[str, Any] = {
            "model": model,
            "api_key": api_key,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if base_url:
            llm_kwargs["base_url"] = base_url
        self.llm = ChatOpenAI(**llm_kwargs)

        self._tools: list[Any] = []
        self._tool_map: dict[str, ToolExecutor] = {}
        self._tool_definitions: list[dict[str, Any]] = []
        if checkpointer is not None:
            self.checkpointer = checkpointer
        else:
            from checkpoint import create_checkpointer
            self.checkpointer = create_checkpointer()
        self._graph = self._build_graph()

        self._stream_cb: Callable[..., Any] | None = None

    def _build_graph(self) -> CompiledStateGraph[Any]:
        """Build the LangGraph StateGraph."""
        builder = StateGraph(AgentState)
        builder.add_node("agent", self._agent_node)
        builder.add_node("tools", self._tools_node)
        builder.set_entry_point("agent")
        builder.add_conditional_edges("agent", self._should_continue, {"tools": "tools", END: END})
        builder.add_edge("tools", "agent")
        return builder.compile(checkpointer=self.checkpointer)

    # ── Public API ─────────────────────────────────────────────

    def set_stream_callback(self, cb: Callable[..., Any]) -> None:
        """Set the callback for streaming events."""
        self._stream_cb = cb

    def bind_tools(self, tools: Sequence[ToolDescriptor]) -> None:
        """Register tool definitions and executors with the graph."""
        for tc in tools:
            definition = {
                "type": "function",
                "function": {
                    "name": tc.name,
                    "description": tc.description,
                    "parameters": tc.parameters or {"type": "object", "properties": {}},
                },
            }
            self._tool_definitions.append(definition)
            self._tool_map[tc.name] = self._wrap_tool(tc)

    @staticmethod
    def _wrap_tool(tc: ToolDescriptor) -> ToolExecutor:
        """Wrap a ToolDescriptor into a ToolExecutor for the tools node."""
        return _InlineToolExecutor(tc)

    @property
    def graph(self) -> CompiledStateGraph[Any]:
        """Return the compiled LangGraph state graph."""
        return self._graph

    def with_config(self, **kwargs: Any) -> SingleAgentGraph:
        """Return self (config passthrough for interface compatibility)."""
        return self

    async def run(
        self,
        requirement: str,
        system_prompt: str = "",
        session_context: str = "",
        chat_history: list[Any] | None = None,
        thread_id: str = "",
        run_id: str = "",
        no_rag_hits: bool = False,
    ) -> dict[str, Any]:
        """Run the agent graph with the given requirement and return results."""
        if run_id:
            for wrapper in self._tool_map.values():
                wrapper.set_run_id(run_id)
        config = cast(
            RunnableConfig,
            {
                "configurable": {"thread_id": thread_id or run_id or str(id(self))},
                "recursion_limit": 100,
            },
        )
        initial_messages = list(chat_history) if chat_history else []
        initial_messages.append(HumanMessage(content=requirement))
        result = await self._graph.ainvoke(
            {
                "messages": initial_messages,
                "system_prompt": system_prompt,
                "session_context": session_context,
                "no_rag_hits": no_rag_hits,
            },
            config,
        )
        usage = self._last_usage or {}
        return {
            "messages": result.get("messages", []),
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "model": self.model,
        }

    async def arun(
        self, message: str, system_prompt: str = "", session_context: str = "", no_rag_hits: bool = False
    ) -> str:
        """Run one turn synchronously and return the response text."""
        config = cast(RunnableConfig, {"configurable": {"thread_id": str(id(self))}, "recursion_limit": 25})
        result = await self._graph.ainvoke(
            {
                "messages": [HumanMessage(content=message)],
                "system_prompt": system_prompt,
                "session_context": session_context,
                "no_rag_hits": no_rag_hits,
            },
            config,
        )
        return result["messages"][-1].content if result.get("messages") else ""
