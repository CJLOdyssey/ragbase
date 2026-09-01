"""LLM SSE streaming — parse chunks, emit callbacks, record metrics.

Splitters and request-building live in ``splitters`` / ``request_builder``;
this module re-exports their public functions for backward compatibility.
"""

from __future__ import annotations

import contextlib
import json
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

from streaming.request_builder import (  # noqa: E402  # re-exported for backward compat
    build_llm_request_body,
    build_tool_calls_list,
    convert_messages_to_api,
)
from streaming.splitters import ReasoningSplitter, ThinkTagSplitter  # noqa: E402

__all__ = [
    "stream_llm_response",
    "build_llm_request_body",
    "build_tool_calls_list",
    "convert_messages_to_api",
    "ThinkTagSplitter",
    "ReasoningSplitter",
]

logger = get_logger(__name__)


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
        await llm_circuit.acquire()
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
        logger.error("Raw LLM stream failed", exc_info=True)
        llm_requests_total.labels(model=_model_name, status="error").inc()
        await llm_circuit.record_failure()
        raise
    else:
        await llm_circuit.record_success()

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
