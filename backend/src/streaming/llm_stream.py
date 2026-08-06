"""LLM streaming helpers: message conversion + SSE parsing + request building."""

from __future__ import annotations

import contextlib
import json
import logging
import time
from typing import Any

import httpx
from core.infra.circuit_breaker import CircuitBreakerOpenError, llm_circuit
from core.infra.logging_config import get_logger
from core.infra.metrics import (
    llm_request_duration_seconds,
    llm_requests_total,
    llm_tokens_total,
)

# Hard guard on runaway SSE streams (free-tier LLMs can stream forever, each
# chunk resetting httpx's read timeout). Truncate past this many SSE lines.
_MAX_STREAM_LINES = 2000
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

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


async def stream_llm_response(
    url: str,
    headers: dict[str, Any],
    body: dict[str, Any],
    stream_cb: Any = None,
    tool_definitions: list[dict[str, Any]] | None = None,
) -> tuple[list[str], list[str], dict[int, dict[str, Any]], str | None, dict[str, Any]]:
    """Stream SSE from the LLM endpoint, parse chunks, emit callbacks.

    Returns (content_chunks, thinking_chunks, tool_calls_map, finish_reason, usage_info).
    """
    content_chunks: list[str] = []
    thinking_chunks: list[str] = []
    tool_calls_map: dict[int, dict[str, Any]] = {}
    finish_reason: str | None = None
    _thinking_flushed = False
    _pending_content: list[str] = []
    _tool_calls_seen = False
    usage_info: dict[str, Any] = {}
    _start_time = time.time()
    _model_name = body.get("model", "unknown")

    # Circuit breaker guard — rejects the call if LLM API is in failure state
    try:
        await llm_circuit._acquire()
    except CircuitBreakerOpenError:
        logger.error("Circuit breaker open — rejecting LLM call (%s failures)", llm_circuit.failures)
        raise

    try:
        async with (
            httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=15.0), proxy=None) as client,
            client.stream("POST", url, headers=headers, json=body) as response,
        ):
            if response.status_code != 200:
                body_text = await response.aread()
                error_body = body_text.decode(errors="replace")[:1000]
                logger.error("LLM API error: status=%d body=%s", response.status_code, error_body)
            response.raise_for_status()
            _line_n = 0
            async for line in response.aiter_lines():
                _line_n += 1
                if _line_n > _MAX_STREAM_LINES:
                    # Hard guard: runaway model output (free-tier LLMs can stream
                    # forever, resetting the read timeout with each chunk) must not
                    # pin the worker indefinitely. Truncate and treat as finished.
                    logger.warning(
                        "LLM stream truncated at %d lines (guard) | url=%s",
                        _MAX_STREAM_LINES, url,
                    )
                    break
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                choices = chunk.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                fr = choices[0].get("finish_reason")
                if fr:
                    finish_reason = fr
                    usage_info = chunk.get("usage", {}) or usage_info

                rc = delta.get("reasoning_content")
                if rc:
                    thinking_chunks.append(rc)
                    if stream_cb:
                        with contextlib.suppress(Exception):
                            await stream_cb({"event": "on_custom_thinking", "data": {"content": rc}})

                content = delta.get("content")
                if content:
                    if thinking_chunks and not _thinking_flushed:
                        _thinking_flushed = True
                    if _tool_calls_seen or not tool_definitions:
                        content_chunks.append(content)
                        if stream_cb:
                            await stream_cb({"event": "on_custom_token", "data": {"content": content}})
                    else:
                        _pending_content.append(content)

                tc_delta = delta.get("tool_calls")
                if tc_delta:
                    if not _tool_calls_seen:
                        _tool_calls_seen = True
                        _pending_content.clear()
                    for tc in tc_delta:
                        idx = tc.get("index", 0)
                        if idx not in tool_calls_map:
                            tool_calls_map[idx] = {"id": tc.get("id", ""), "name": "", "arguments": ""}
                        fn = tc.get("function", {})
                        if fn.get("name"):
                            tool_calls_map[idx]["name"] += fn["name"]
                        if fn.get("arguments"):
                            tool_calls_map[idx]["arguments"] += fn["arguments"]
                        if tc.get("id"):
                            tool_calls_map[idx]["id"] = tc["id"]

    except httpx.HTTPError:
        logging.getLogger(__name__).error("Raw LLM stream failed", exc_info=True)
        llm_requests_total.labels(model=_model_name, status="error").inc()
        await llm_circuit._on_failure()
        raise
    else:
        await llm_circuit._on_success()

    if _pending_content and not _tool_calls_seen and tool_definitions:
        for chunk in _pending_content:
            content_chunks.append(chunk)
            if stream_cb:
                await stream_cb({"event": "on_custom_token", "data": {"content": chunk}})
    _pending_content.clear()

    # Record application-level metrics
    _elapsed = time.time() - _start_time
    if finish_reason == "stop":
        llm_requests_total.labels(model=_model_name, status="success").inc()
    else:
        llm_requests_total.labels(model=_model_name, status=finish_reason or "unknown").inc()
    llm_request_duration_seconds.labels(model=_model_name).observe(_elapsed)
    if usage_info:
        prompt_tokens = usage_info.get("prompt_tokens", 0)
        completion_tokens = usage_info.get("completion_tokens", 0)
        if prompt_tokens:
            llm_tokens_total.labels(model=_model_name, type="prompt").inc(prompt_tokens)
        if completion_tokens:
            llm_tokens_total.labels(model=_model_name, type="completion").inc(completion_tokens)

    return content_chunks, thinking_chunks, tool_calls_map, finish_reason, usage_info
