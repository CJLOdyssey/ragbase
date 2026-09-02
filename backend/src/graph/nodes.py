"""Graph node methods — mixed into SingleAgentGraph.

Methods keep ``self`` references intact; moving them out of graph.py was purely
a file-size split (SPEC: single file <= 400 lines), no logic changed.
"""

import contextlib
import json
from collections.abc import Callable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from core._interfaces import StreamResponseHandler
from core.infra.logging_config import get_logger
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END
from streaming.llm_stream import (
    build_llm_request_body,
    build_tool_calls_list,
    convert_messages_to_api,
    stream_llm_response,
)

from graph.graph_state import AgentState
from graph.helpers import (
    CONTEXT_GUARD_PROMPT,
    NO_RAG_HITS_PROMPT,
    _emit_balance_warning,
    _is_balance_error,
    _load_context_guard_template,
)

logger = get_logger(__name__)


class GraphNodesMixin:
    """LangGraph node implementations for SingleAgentGraph.

    Attribute declarations satisfy mypy strict for fields owned by
    ``SingleAgentGraph.__init__``.
    """

    _stream_cb: Callable[..., Any] | None
    _tool_definitions: list[dict[str, Any]]
    _last_usage: dict[str, Any]
    model: str
    api_key: str
    base_url: str | None
    temperature: float
    max_tokens: int
    image_model: bool
    llm: Any

    async def _raw_llm_stream(
        self,
        messages: list[BaseMessage],
        _stream_handler: StreamResponseHandler = stream_llm_response,
    ) -> tuple[str, str, list[dict[str, Any]]]:
        """Async raw HTTP streaming — captures content + reasoning_content + tool_calls."""
        api_messages = convert_messages_to_api(messages)
        url, headers, body = build_llm_request_body(
            api_messages,
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            tool_definitions=self._tool_definitions,
        )

        try:
            content_chunks, thinking_chunks, tool_calls_map, finish_reason, usage_info = (
                await _stream_handler(url, headers, body, self._stream_cb, self._tool_definitions)
            )
        except httpx.HTTPStatusError as exc:
            error_detail = ""
            if exc.response is not None:
                try:
                    error_detail = exc.response.text[:1000]
                except Exception:
                    error_detail = str(exc)[:1000]
            logger.error("LLM API rejected request | status=%s | body=%s",
                         exc.response.status_code if exc.response else "?", error_detail)

            # Detect balance/quota errors and warn the user via frontend
            if _is_balance_error(error_detail) and self._stream_cb:
                await _emit_balance_warning(self._stream_cb)

            raise

        full_content = "".join(content_chunks)
        thinking = "".join(thinking_chunks).strip()

        final_tool_calls = build_tool_calls_list(tool_calls_map)

        logger.info(
            "Raw LLM | content=%d chars | thinking=%d chars | tool_calls=%d | finish=%s",
            len(full_content), len(thinking), len(final_tool_calls), finish_reason,
        )
        if final_tool_calls:
            for tc in final_tool_calls:
                logger.info(
                    "  tool=%s args=%s",
                    tc["name"],
                    json.dumps(tc.get("args", {}), ensure_ascii=False)[:200],
                )
        self._last_usage = usage_info
        return full_content, thinking, final_tool_calls

    # ── Graph nodes ────────────────────────────────────────────

    async def _agent_node(self, state: AgentState) -> dict[str, Any]:
        """LangGraph agent node — builds messages, calls LLM, returns AIMessage."""
        if self.image_model:
            return await self._image_node(state)
        messages = state.get("messages", [])
        system_prompt = state.get("system_prompt", "")
        session_context = state.get("session_context", "")

        full_messages: list[BaseMessage] = []
        # Explicit Beijing timezone — the server may run in UTC/Docker where
        # astimezone() would report the wrong clock under the CST label.
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
        weekday_cn = ["一", "二", "三", "四", "五", "六", "日"][now.weekday()]
        date_context = (
            f"当前日期：{now.year}年{now.month}月{now.day}日 周{weekday_cn} "
            f"{now.hour:02d}:{now.minute:02d}（北京时间 CST）"
        )
        full_messages.append(SystemMessage(content=date_context))
        if system_prompt:
            full_messages.append(SystemMessage(content=system_prompt))
        # R1: zero retrieval hits → deterministic refusal guidance. Conditioned
        # on state.no_rag_hits only — never inject with context present (the
        # unconditional phrasing caused the answer_relevancy 0.253 regression).
        if state.get("no_rag_hits"):
            full_messages.append(SystemMessage(content=NO_RAG_HITS_PROMPT))
        if session_context:
            # OWASP LLM01: untrusted retrieval/attachment text is sanitized
            # deterministically (instruction markers neutralized — the model
            # never sees the instruction text) and framed by the DB-configured
            # guard template. No template configured → inject sanitized text
            # plain rather than break the chat.
            from rag.rag_guard import sanitize_context

            safe_ctx = sanitize_context(session_context)
            template = await _load_context_guard_template()
            if template:
                content = template.replace("{context}", safe_ctx)
            else:
                logger.debug(
                    "context guard prompt %r not configured — injecting sanitized context",
                    CONTEXT_GUARD_PROMPT,
                )
                content = safe_ctx
            full_messages.append(SystemMessage(content=content))
        full_messages.extend(messages)
        content, thinking, raw_tool_calls = await self._raw_llm_stream(full_messages)

        kwargs: dict[str, Any] = {"content": content}
        if raw_tool_calls:
            kwargs["tool_calls"] = [
                {"name": tc["name"], "args": tc["args"], "id": tc["id"]}
                for tc in raw_tool_calls
            ]
        if thinking:
            kwargs["additional_kwargs"] = {"thinking": thinking}

        if thinking:
            thinking_nodes: list[dict[str, Any]] = [{"type": "thought", "content": thinking}]
            for tc in (raw_tool_calls or []):
                tc_name = tc.get("name", "")
                tc_args = tc.get("args", {})
                thinking_nodes.append({
                    "type": "tool_call",
                    "content": f"Calling {tc_name}",
                    "toolName": tc_name,
                    "toolParams": {k: str(v) for k, v in tc_args.items()} if tc_args else {},
                })
            if self._stream_cb:
                with contextlib.suppress(Exception):
                    await self._stream_cb({
                        "event": "on_thinking_nodes",
                        "data": {"nodes": thinking_nodes},
                    })
        if self._stream_cb:
            with contextlib.suppress(Exception):
                await self._stream_cb({"event": "on_node_end", "data": {}})

        return {"messages": [AIMessage(**kwargs)]}

    async def _image_node(self, state: AgentState) -> dict[str, Any]:
        """Image-model node — calls the provider's /images/generations endpoint.

        Non-chat models (model_types == "image", e.g. Kwai-Kolors/Kolors) cannot
        consume chat prompts: the last user message text is used as the prompt
        and the generated image URL is returned as markdown so the existing
        frontend markdown renderer displays it inline.
        """
        messages = state.get("messages", [])
        prompt = ""
        for m in reversed(messages):
            if getattr(m, "type", "") == "human":
                prompt = str(m.content or "")
                break
        if not prompt.strip():
            prompt = "请生成一张图片"

        if self._stream_cb:
            with contextlib.suppress(Exception):
                await self._stream_cb({
                    "event": "on_custom_thinking",
                    "data": {"content": f"正在使用 {self.model} 生成图片…"},
                })

        from streaming.image_generation import generate_image

        image_url = await generate_image(
            self.api_key,
            prompt,
            model=self.model,
            base_url=self.base_url,
        )
        content = f"![生成的图片]({image_url})"

        if self._stream_cb:
            with contextlib.suppress(Exception):
                await self._stream_cb({
                    "event": "on_custom_token",
                    "data": {"content": content},
                })
            with contextlib.suppress(Exception):
                await self._stream_cb({"event": "on_node_end", "data": {}})

        return {"messages": [AIMessage(content=content)]}

    async def _tools_node(self, state: AgentState) -> dict[str, Any]:
        """LangGraph tools node — returns error for any tool calls (no tools registered)."""
        messages = state.get("messages", [])
        last_msg = messages[-1] if messages else None
        if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
            return {}

        tool_messages = []
        for tc in last_msg.tool_calls:
            tool_name = tc.get("name", "")
            tool_args = tc.get("args", {})
            tool_id = tc.get("id", "")

            # ── Emit tool-call start into thinking chain ──
            if self._stream_cb:
                args_preview = json.dumps(tool_args, ensure_ascii=False)[:200]
                with contextlib.suppress(Exception):
                    await self._stream_cb({
                        "event": "on_custom_thinking",
                        "data": {"content": f"[tool] {tool_name}({args_preview})"},
                    })

            result = f"Unknown tool: {tool_name}"
            logger.info(
                "Tool result | tool=%s | result_len=%d | has_cb=%s",
                tool_name, len(str(result or "")), self._stream_cb is not None,
            )

            tool_messages.append(
                ToolMessage(content=str(result or ""), tool_call_id=tool_id, name=tool_name)
            )

            # ── Emit tool result into thinking chain ──
            if self._stream_cb:
                result_str = str(result or "")[:200]
                with contextlib.suppress(Exception):
                    await self._stream_cb({
                        "event": "on_custom_thinking",
                        "data": {"content": f"[result] {tool_name} | {result_str}"},
                    })
        if self._stream_cb:
            with contextlib.suppress(Exception):
                await self._stream_cb({"event": "on_node_end", "data": {}})
        return {"messages": tool_messages}

    def _should_continue(self, state: AgentState) -> str:
        """Edge: continue if last message has tool_calls, else END."""
        messages = state.get("messages", [])
        if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
            return "tools"
        return END
