"""LLM streaming helpers: message conversion + SSE parsing + request building."""

from __future__ import annotations

import contextlib
import json
import logging
import os
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
#
# The model supports up to MAX_STREAM_TOKENS output tokens; reasoning models
# (DeepSeek-R1) can emit very long chain-of-thought, so the line budget must
# comfortably fit that (SSE emits ~one token per line on these providers).
# Configurable via LLM_MAX_STREAM_LINES; defaults to 4x the token budget.
_MAX_STREAM_TOKENS = int(os.environ.get("LLM_MAX_STREAM_TOKENS", "16384"))
_MAX_STREAM_LINES = int(os.environ.get("LLM_MAX_STREAM_LINES", str(_MAX_STREAM_TOKENS * 4)))
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

logger = get_logger(__name__)


class ThinkTagSplitter:
    """Streaming splitter for models that emit chain-of-thought inside <think>.

    Some providers (e.g. SiliconFlow's GLM-Z1) return reasoning inline in
    ``content`` wrapped in ``<think>...</think>`` instead of via
    ``reasoning_content``. This state machine accumulates those tags across SSE
    chunks and routes the enclosed text to "thinking" and everything else to
    "content", so the UI can render the chain-of-thought separately.
    """

    __slots__ = ("_in_think", "_buffer")

    def __init__(self) -> None:
        self._in_think = False
        self._buffer: list[str] = []

    def feed(self, text: str) -> tuple[list[str], list[str]]:
        """Process one content chunk; return (thinking_parts, content_parts)."""
        thinking: list[str] = []
        content: list[str] = []
        rest = text
        while rest:
            tag = "</think>" if self._in_think else "<think>"
            idx = rest.find(tag)
            if idx < 0:
                if self._in_think:
                    self._buffer.append(rest)
                else:
                    content.append(rest)
                break
            head, tail = rest[:idx], rest[idx + len(tag):]
            if self._in_think:
                self._buffer.append(head)
                thinking.append("".join(self._buffer))
                self._buffer = []
                self._in_think = False
            else:
                if head:
                    content.append(head)
                self._in_think = True
            rest = tail
        return thinking, content

    def finish(self) -> tuple[str | None, str | None]:
        """Flush any trailing buffer. Returns (leftover_thinking, leftover_content)."""
        leftover = "".join(self._buffer)
        self._buffer = []
        if leftover:
            if self._in_think:
                self._in_think = False
                return leftover, None
            return None, leftover
        return None, None



class ReasoningSplitter:
    """Streaming splitter for ``reasoning_content`` that carries a <think> tag.

    SiliconFlow's GLM-Z1 emits chain-of-thought in ``reasoning_content``
    wrapped in ``<think>`` — but the tag is sliced across SSE chunks
    (``'<th'`` + ``'ink'`` + ``'>'``) and the closing tag is often omitted
    entirely. Unlike ``ThinkTagSplitter`` (which requires the full tag in one
    chunk and explicit closing), this state machine accumulates text across
    chunks, strips a fully-assembled opening ``<think>``, and treats every
    subsequent chunk as thinking until the stream ends.
    """

    __slots__ = ("_pending", "_in_think")

    _OPEN_TAG = "<think>"

    def __init__(self) -> None:
        self._pending: list[str] = []
        self._in_think = False

    def feed(self, text: str) -> list[str]:
        """Process one reasoning chunk; return thinking parts to emit."""
        if self._in_think:
            # Tag already stripped — everything else is chain-of-thought.
            return [text] if text else []

        self._pending.append(text)
        joined = "".join(self._pending)
        idx = joined.find(self._OPEN_TAG)
        if idx < 0:
            # Tag not fully assembled yet — hold the whole buffer. Cap it so a
            # missing opening tag can't pin memory (shouldn't happen: provider
            # sends the tag first).
            if len(joined) > 512:
                dropped = "".join(self._pending)
                self._pending = []
                return [dropped] if dropped else []
            return []

        # Opening tag assembled — strip it and flush any text before it.
        tail = joined[idx + len(self._OPEN_TAG):]
        self._pending = []
        self._in_think = True
        before = joined[:idx]
        out: list[str] = [before] if before else []
        if tail:
            out.append(tail)
        return out

    def finish(self) -> str | None:
        """Flush any remaining buffered thinking text."""
        leftover = "".join(self._pending)
        self._pending = []
        self._in_think = False
        return leftover or None


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
    _think_splitter = ThinkTagSplitter()
    _reasoning_splitter = ReasoningSplitter()
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
                    # reasoning_content carries a <think> tag that is sliced
                    # across SSE chunks and often has no closing tag. Strip it
                    # cross-chunk and emit the cleaned chain-of-thought inline
                    # so thinking streams BEFORE the answer, not after.
                    for part in _reasoning_splitter.feed(rc):
                        thinking_chunks.append(part)
                        if stream_cb:
                            with contextlib.suppress(Exception):
                                await stream_cb({"event": "on_custom_thinking", "data": {"content": part}})

                content = delta.get("content")
                if content:
                    think_parts, body_parts = _think_splitter.feed(content)
                    for part in think_parts:
                        thinking_chunks.append(part)
                        if stream_cb:
                            with contextlib.suppress(Exception):
                                await stream_cb({"event": "on_custom_thinking", "data": {"content": part}})
                    if not body_parts:
                        continue
                    if thinking_chunks and not _thinking_flushed:
                        _thinking_flushed = True
                    if _tool_calls_seen or not tool_definitions:
                        for part in body_parts:
                            content_chunks.append(part)
                            if stream_cb:
                                await stream_cb({"event": "on_custom_token", "data": {"content": part}})
                    else:
                        _pending_content.extend(body_parts)

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

    # Flush any trailing <think> block that wasn't explicitly closed (some
    # models omit the closing tag on truncation) and leftover content.
    leftover_thinking, leftover_content = _think_splitter.finish()
    if leftover_thinking:
        thinking_chunks.append(leftover_thinking)
        if stream_cb:
            with contextlib.suppress(Exception):
                await stream_cb({"event": "on_custom_thinking", "data": {"content": leftover_thinking}})
    if leftover_content and (not tool_definitions or _tool_calls_seen):
        content_chunks.append(leftover_content)
        if stream_cb:
            await stream_cb({"event": "on_custom_token", "data": {"content": leftover_content}})

    # reasoning_content is emitted inline via _reasoning_splitter; flush any
    # buffered text whose opening <think> never fully assembled.
    r_leftover = _reasoning_splitter.finish()
    if r_leftover:
        thinking_chunks.append(r_leftover)
        if stream_cb:
            with contextlib.suppress(Exception):
                await stream_cb({"event": "on_custom_thinking", "data": {"content": r_leftover}})

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
