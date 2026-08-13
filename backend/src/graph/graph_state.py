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
    # True when retrieval returned zero hits — _agent_node injects the
    # deterministic refusal guidance (NO_RAG_HITS_PROMPT) instead of letting
    # the model answer with no knowledge-base context (R1).
    no_rag_hits: bool


__all__ = ["AgentState"]
