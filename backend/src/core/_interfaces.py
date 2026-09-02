"""Abstract Protocol interfaces for decoupling the agent graph engine.

These protocols define the contracts that ``graph.py`` (SingleAgentGraph)
depends on, allowing tests and alternative implementations to substitute
concrete classes from ``llm_stream.py``.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable


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


__all__ = ["StreamResponseHandler"]
