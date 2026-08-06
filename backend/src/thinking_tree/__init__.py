"""Thinking Tree types — structured nodes for reasoning visualization."""

from dataclasses import dataclass
from typing import Literal

ThinkingNodeType = Literal["thought", "tool_call"]


@dataclass
class RefLink:
    """A reference link from a search/tool result."""

    title: str
    url: str
    snippet: str | None = None


@dataclass
class ThinkingNode:
    """A single node in the thinking tree.

    - ``thought`` nodes: regular reasoning text (same as before)
    - ``tool_call`` nodes: tool invocations with name, params, and optional references
    """

    type: ThinkingNodeType
    content: str
    tool_name: str | None = None
    tool_params: dict[str, str] | None = None
    references: list[RefLink] | None = None
