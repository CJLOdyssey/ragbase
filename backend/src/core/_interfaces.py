"""Abstract Protocol interfaces for decoupling the agent graph engine.

These protocols define the contracts that ``graph.py`` (SingleAgentGraph)
depends on, allowing tests and alternative implementations to substitute
concrete classes from ``tool_config.py`` and ``llm_stream.py``.
"""
# ▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ToolDescriptor(Protocol):
    """Read-only metadata required to register a tool with the agent graph.

    Structural subtype of ``ToolConfig`` — every ``ToolConfig`` instance
    satisfies this protocol automatically.
    """

    name: str
    description: str
    parameters: dict[str, Any] | None
    instructions: str
    mcp_type: str
    mcp_endpoint: str
    mcp_tool_name: str
    endpoint: str
    method: str
    headers: str


@runtime_checkable
class ToolExecutor(Protocol):
    """Contract for a tool wrapper that the graph's ``_tools_node`` can invoke.

    Structural subtype of ``_ToolWrapper`` — every ``_ToolWrapper`` instance
    satisfies this protocol automatically.
    """

    name: str
    description: str

    async def invoke(self, args: dict[str, Any]) -> str: ...

    def set_llm(self, llm: Any) -> None: ...

    def set_run_id(self, run_id: str) -> None: ...


@runtime_checkable
class StreamResponseHandler(Protocol):
    """Contract for the LLM streaming response parser.

    Structural subtype of ``stream_llm_response``.
    """

    async def __call__(
        self,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any],
        stream_cb: Callable[..., Any] | None,
        tool_definitions: list[dict[str, Any]],
    ) -> tuple[list[str], list[str], dict[int, dict[str, Any]], str | None, dict[str, Any]]: ...


__all__ = ["ToolDescriptor", "ToolExecutor", "StreamResponseHandler"]
