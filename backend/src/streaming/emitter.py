"""Streaming emitter — bridges raw httpx streaming events to Redis pub/sub + DB."""

import logging
import os
from typing import Any

from broker import publish_run_message
from core.infra.metrics import stream_messages_dropped_total
from repository import save_message

logger = logging.getLogger(__name__)

STREAM_DEFAULT_MAX_BUFFER_SIZE = 20000


class StreamEmitter:
    def __init__(self, run_id: str, sources: list[dict[str, Any]] | None = None):
        self._run_id = run_id
        self._sources = sources or []
        self._message_index = 0
        self._stream_buffer: list[str] = []
        self._thinking_buffer: list[str] = []
        self._buffer_chars: dict[int, int] = {}
        self._pending_thinking: str | None = None
        self._pending_thinking_nodes: list[dict[str, Any]] | None = None
        self._max_buffer_size = self._load_max_buffer_size()
        self._backpressure_warned = False

    @staticmethod
    def _load_max_buffer_size() -> int:
        try:
            return int(os.environ.get("STREAM_MAX_BUFFER_SIZE", str(STREAM_DEFAULT_MAX_BUFFER_SIZE)))
        except (ValueError, TypeError):
            return STREAM_DEFAULT_MAX_BUFFER_SIZE

    def _checked_append(self, buffer: list[str], item: str, label: str) -> None:
        buffer.append(item)
        # Limit by accumulated character count, not chunk count — the model
        # streams 1-2 char chunks, so a 1000-chunk cap truncates the start of
        # long messages. Drop oldest chunks only when total chars overflow.
        buf_id = id(buffer)
        total = self._buffer_chars.get(buf_id, 0) + len(item)
        dropped = 0
        while total - dropped > self._max_buffer_size and len(buffer) > 1:
            removed = buffer.pop(0)
            dropped += len(removed)
        self._buffer_chars[buf_id] = total - dropped
        if dropped:
            stream_messages_dropped_total.inc(dropped)
            if not self._backpressure_warned:
                logger.warning(
                    "Stream buffer exceeded limit for run %s (%s): limit=%d chars, dropping oldest messages",
                    self._run_id, label, self._max_buffer_size,
                )
                self._backpressure_warned = True

    async def __call__(self, event: dict[str, Any]) -> None:
        kind = event.get("event", "")
        data = event.get("data", {})

        if kind == "on_custom_token":
            content = data.get("content", "")
            if content:
                self._checked_append(self._stream_buffer, content, "stream")
                try:
                    await publish_run_message(
                        self._run_id,
                        {
                            "type": "stream",
                            "agent_name": "Agent",
                            "content": content,
                        },
                    )
                except Exception:
                    # Per-token chunk: debug level to avoid log flooding on
                    # sustained Redis issues (final message publish keeps exception).
                    logger.debug("Stream chunk publish failed for run %s", self._run_id, exc_info=True)

        elif kind == "on_custom_thinking":
            rc = data.get("content", "")
            if rc:
                if rc.startswith("[result]"):
                    logger.debug("on_custom_thinking: [result] node received, tool=%s", rc.split(chr(10))[0][:100])
                self._checked_append(self._thinking_buffer, rc, "thinking")
                try:
                    await publish_run_message(
                        self._run_id,
                        {
                            "type": "thinking_stream",
                            "agent_name": "Agent",
                            "content": rc,
                        },
                    )
                except Exception:
                    logger.debug("Thinking stream publish failed for run %s", self._run_id, exc_info=True)

        elif kind == "on_node_end":
            await self._flush_buffers()

        elif kind == "on_chat_model_stream":
            chunk = data.get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                self._checked_append(self._stream_buffer, chunk.content, "stream")

        elif kind == "on_chat_model_end":
            await self._flush_buffers()

        elif kind == "on_chain_end":
            name = event.get("name", "")
            if name == "LangGraph":
                await self._flush_buffers()

        elif kind == "on_thinking_nodes":
            nodes = data.get("nodes", [])
            if nodes:
                self.emit_thinking_nodes(nodes)

        elif kind == "on_tool_complete":
            logger.debug("streaming: on_tool_complete received tool=%s", data.get('toolName'))
            await self.emit_tool_complete(data)

        elif kind == "on_client_action":
            action = data.get("action", {})
            logger.debug("streaming: on_client_action received action=%s", action)
            await publish_run_message(
                self._run_id,
                {
                    "type": "client_action",
                    "agent_name": "Agent",
                    "action": action,
                },
            )

        elif kind == "on_tool_results":
            tool_name = data.get("tool_name", "")
            tool_call_id = data.get("tool_call_id", "")
            refs = data.get("references", [])
            if tool_name and refs:
                await self.emit_tool_results(tool_name, tool_call_id, refs)

        # on_tool_start / on_tool_end are handled at the graph level
        # via on_custom_thinking (see _tools_node in graph.py)

    async def emit_balance_warning(self, message: str = "") -> None:
        await publish_run_message(
            self._run_id,
            {
                "type": "balance_warning",
                "agent_name": "System",
                "content": message or "模型余额不足，请检查 API Key 配置",
            },
        )

    def emit_thinking_nodes(self, nodes: list[dict[str, Any]]) -> None:
        max_pending = 20
        if self._pending_thinking_nodes:
            self._pending_thinking_nodes.extend(nodes)
            if len(self._pending_thinking_nodes) > max_pending:
                self._pending_thinking_nodes = self._pending_thinking_nodes[-max_pending:]
        else:
            self._pending_thinking_nodes = nodes[:max_pending]

    async def emit_tool_results(self, tool_name: str, tool_call_id: str, references: list[dict[str, Any]]) -> None:
        await publish_run_message(
            self._run_id,
            {
                "type": "tool_results",
                "agent_name": "Agent",
                "toolName": tool_name,
                "tool_call_id": tool_call_id,
                "references": references,
            },
        )

    async def emit_tool_complete(self, data: dict[str, Any]) -> None:
        try:
            node = {
                "type": "tool_result",
                "content": f"{data.get('toolName', '')} {'✅ 成功' if data.get('status') == 'success' else '❌ 失败'}",
                "toolName": data.get("toolName", ""),
                "status": data.get("status", "success"),
            }
            logger.debug("emit_tool_complete: publishing node type=%s tool=%s", node['type'], node['toolName'])
            await publish_run_message(
                self._run_id,
                {
                    "type": "tool_complete",
                    "agent_name": "Agent",
                    "node": node,
                },
            )
            logger.debug("emit_tool_complete: published successfully")
        except Exception:
            logger.exception("emit_tool_complete failed")

    async def persist_partial(self) -> None:
        """Persist the un-flushed partial output on cancellation.

        "只要有消息就入库"：run 被取消时，把已流式的半截正文/思考保存为
        chat_message（content 可为空、thinking 可为空，但至少其一非空才会保存）。
        """
        thinking_text = (
            "".join(self._thinking_buffer).strip() if self._thinking_buffer else ""
        )
        full_content = "".join(self._stream_buffer) if self._stream_buffer else ""
        if not thinking_text and not full_content:
            return
        self._stream_buffer.clear()
        self._thinking_buffer.clear()
        self._buffer_chars.clear()
        self._message_index += 1
        try:
            await save_message(
                run_id=self._run_id,
                role="Agent",
                agent_name="Agent",
                content=full_content,
                thinking=thinking_text or None,
                round_number=self._message_index,
                sources=self._sources or None,
            )
            logger.info(
                "Partial message persisted for cancelled run %s (content=%d, thinking=%d)",
                self._run_id, len(full_content), len(thinking_text),
            )
        except Exception:
            logger.exception("Persist partial failed for run %s", self._run_id)

    async def _flush_buffers(self) -> None:
        thinking_text = ""
        if self._thinking_buffer:
            thinking_text = "".join(self._thinking_buffer).strip()
            self._thinking_buffer.clear()
            self._buffer_chars.pop(id(self._thinking_buffer), None)

        has_pending = self._pending_thinking is not None
        if has_pending:
            logger.debug("_flush_buffers: pending_thinking exists, len=%d, has_tool_result=%s",
                         len(self._pending_thinking or ""), "[result]" in (self._pending_thinking or ""))
        if thinking_text and "[result]" in thinking_text:
            logger.debug("_flush_buffers: thinking_text has [result], len=%d", len(thinking_text))
        elif thinking_text:
            logger.debug("_flush_buffers: thinking_text without [result], len=%d, content=%s...",
                         len(thinking_text), thinking_text[:80])

        # Merge pending thinking from a previous tools-only flush with current thinking
        if self._pending_thinking:
            thinking_text = (
                self._pending_thinking + "\n\n" + thinking_text if thinking_text else self._pending_thinking
            )
            self._pending_thinking = None

        saved_with_content = False
        if self._stream_buffer:
            full_content = "".join(self._stream_buffer)
            self._stream_buffer.clear()
            self._buffer_chars.pop(id(self._stream_buffer), None)
            self._message_index += 1
            try:
                await publish_run_message(
                    self._run_id,
                    {
                        "type": "message",
                        "role": "Agent",
                        "agent_name": "Agent",
                        "content": full_content,
                        "round_number": self._message_index,
                        "sources": self._sources,
                    },
                )
            except Exception:
                logger.exception("Stream publish failed for run %s", self._run_id)
            try:
                await save_message(
                    run_id=self._run_id,
                    role="Agent",
                    agent_name="Agent",
                    content=full_content,
                    thinking=thinking_text,
                    round_number=self._message_index,
                    sources=self._sources,
                )
                saved_with_content = True
            except Exception:
                # Publish and save are independent: a failed publish must not
                # drop the message from history (and vice versa).
                logger.exception("Stream save failed for run %s", self._run_id)

        if thinking_text:
            try:
                payload: dict[str, Any] = {
                    "type": "thinking_done",
                    "agent_name": "Agent",
                    "thinking": thinking_text,
                }
                if self._pending_thinking_nodes:
                    payload["nodes"] = self._pending_thinking_nodes
                    self._pending_thinking_nodes = None
                await publish_run_message(self._run_id, payload)
            except Exception:
                logger.exception("Thinking publish failed for run %s", self._run_id)
            # Tools-only flush: has thinking but no content to save with.
            # Cache it as pending so the next content flush carries it to DB.
            if not saved_with_content:
                self._pending_thinking = thinking_text

    async def _emit(
        self, agent_name: str, content: str, msg_type: str = "message", thinking: str | None = None
    ) -> None:
        self._message_index += 1
        payload = {
            "type": msg_type,
            "role": agent_name,
            "agent_name": agent_name,
            "content": content,
            "round_number": self._message_index,
        }
        if msg_type == "message" and self._sources:
            payload["sources"] = self._sources
        if not thinking and self._pending_thinking:
            thinking = self._pending_thinking
            self._pending_thinking = None
        if thinking:
            payload["thinking"] = thinking
        try:
            await publish_run_message(self._run_id, payload)
            if msg_type == "message":
                await save_message(
                    run_id=self._run_id,
                    role=agent_name,
                    agent_name=agent_name,
                    content=content,
                    thinking=thinking,
                    round_number=self._message_index,
                    sources=self._sources or None,
                )
        except Exception:
            logger.exception("Stream emit failed for run %s", self._run_id)
