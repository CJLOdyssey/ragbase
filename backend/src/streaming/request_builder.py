"""LLM request building — message conversion + HTTP request body assembly."""

import json
from typing import Any

from core.infra.logging_config import get_logger
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

logger = get_logger(__name__)


def convert_messages_to_api(messages: list[BaseMessage]) -> list[dict[str, Any]]:
    """Convert LangChain BaseMessage list to OpenAI API message dicts."""
    api_messages = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            api_messages.append({"role": "system", "content": msg.content})
        elif isinstance(msg, HumanMessage):
            api_messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            entry: dict[str, Any] = {"role": "assistant", "content": msg.content}
            if msg.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": json.dumps(tc["args"])},
                    }
                    for tc in msg.tool_calls
                ]
            api_messages.append(entry)
        elif isinstance(msg, ToolMessage):
            api_messages.append({"role": "tool", "tool_call_id": msg.tool_call_id, "content": msg.content})
    return api_messages


def build_llm_request_body(
    api_messages: list[dict[str, Any]],
    *,
    model: str,
    api_key: str,
    base_url: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 16384,
    tool_definitions: list[dict[str, Any]] | None = None,
) -> tuple[str, dict[str, str], dict[str, Any]]:
    """Build the HTTP request URL, headers, and JSON body for LLM chat completion.

    Returns ``(url, headers, body)``.
    """
    url = f"{(base_url or 'https://api.deepseek.com').rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    body: dict[str, Any] = {
        "model": model,
        "messages": api_messages,
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if tool_definitions:
        body["tools"] = tool_definitions
        body["tool_choice"] = "auto"

    is_deepseek = "deepseek" in (base_url or "").lower() or "deepseek" in model.lower()
    if is_deepseek and not tool_definitions:
        body["thinking"] = {"type": "enabled"}

    logger.info(
        "LLM request | model=%s | msgs=%d | tools=%d | thinking=%s",
        model, len(api_messages), len(tool_definitions or []),
        "thinking" in body,
    )
    if tool_definitions:
        logger.info(
            "Tools sent: %s",
            json.dumps([t["function"]["name"] for t in tool_definitions]),
        )

    return url, headers, body


def build_tool_calls_list(tool_calls_map: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    """Consolidate streaming tool-call fragments into final list."""
    final = []
    for idx in sorted(tool_calls_map):
        tc = tool_calls_map[idx]
        if tc["name"]:
            try:
                args = json.loads(tc["arguments"]) if tc["arguments"] else {}
            except json.JSONDecodeError:
                args = {}
            final.append({"id": tc["id"], "name": tc["name"], "args": args})
    return final
