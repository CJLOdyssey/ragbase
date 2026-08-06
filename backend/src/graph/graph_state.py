"""AgentState TypedDict and shared type definitions for the LangGraph agent engine."""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """TypedDict defining the LangGraph agent state schema."""

    messages: Annotated[list[BaseMessage], add_messages]
    system_prompt: str
    session_context: str


__all__ = ["AgentState"]
