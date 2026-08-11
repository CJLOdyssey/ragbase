"""Comprehensive tests for backend/streaming/emitter.py — all event handlers and edge cases."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.requirement("REQ-RUN-002")
class TestStreamEmitterInit:
    """StreamEmitter initialization tests."""

    def test_init_attributes(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-abc")
        assert emitter._run_id == "run-abc"
        assert emitter._message_index == 0
        assert emitter._stream_buffer == []
        assert emitter._thinking_buffer == []
        assert emitter._pending_thinking is None
        assert emitter._pending_thinking_nodes is None


@pytest.mark.requirement("REQ-RUN-002")
class TestOnCustomToken:
    """Tests for on_custom_token event handling."""

    @pytest.mark.asyncio
    async def test_appends_content_and_publishes(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-1")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter({"event": "on_custom_token", "data": {"content": "hello"}})
            assert emitter._stream_buffer == ["hello"]
            mock_pub.assert_awaited_once_with(
                "run-1",
                {"type": "stream", "agent_name": "Agent", "content": "hello"},
            )

    @pytest.mark.asyncio
    async def test_empty_content_skips(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-2")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter({"event": "on_custom_token", "data": {"content": ""}})
            assert emitter._stream_buffer == []
            mock_pub.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_content_key_skips(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-3")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter({"event": "on_custom_token", "data": {}})
            assert emitter._stream_buffer == []
            mock_pub.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_publish_failure_still_appends(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-4")
        with patch("streaming.emitter.publish_run_message", side_effect=Exception("redis down")):
            await emitter({"event": "on_custom_token", "data": {"content": "chunk"}})
            assert emitter._stream_buffer == ["chunk"]


@pytest.mark.requirement("REQ-RUN-002")
class TestOnCustomThinking:
    """Tests for on_custom_thinking event handling."""

    @pytest.mark.asyncio
    async def test_appends_thinking_and_publishes(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-5")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter({"event": "on_custom_thinking", "data": {"content": "reasoning"}})
            assert emitter._thinking_buffer == ["reasoning"]
            mock_pub.assert_awaited_once_with(
                "run-5",
                {"type": "thinking_stream", "agent_name": "Agent", "content": "reasoning"},
            )

    @pytest.mark.asyncio
    async def test_empty_content_skips(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-6")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter({"event": "on_custom_thinking", "data": {"content": ""}})
            assert emitter._thinking_buffer == []
            mock_pub.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_publish_failure_still_appends(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-7")
        with patch("streaming.emitter.publish_run_message", side_effect=Exception("redis down")):
            await emitter({"event": "on_custom_thinking", "data": {"content": "thought"}})
            assert emitter._thinking_buffer == ["thought"]


@pytest.mark.requirement("REQ-RUN-002")
class TestOnNodeEnd:
    """Tests for on_node_end event — flushes both buffers."""

    @pytest.mark.asyncio
    async def test_flushes_stream_and_thinking_buffers(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-8")
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock),
            patch("streaming.emitter.save_message", new_callable=AsyncMock),
        ):
            emitter._stream_buffer = ["a", "b"]
            emitter._thinking_buffer = ["t1"]
            await emitter({"event": "on_node_end", "data": {}})
            assert emitter._stream_buffer == []
            assert emitter._thinking_buffer == []
            assert emitter._message_index == 1

    @pytest.mark.asyncio
    async def test_flush_with_empty_buffers_no_publish(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-9")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter({"event": "on_node_end", "data": {}})
            mock_pub.assert_not_awaited()


@pytest.mark.requirement("REQ-RUN-002")
class TestOnChatModelStream:
    """Tests for on_chat_model_stream event."""

    @pytest.mark.asyncio
    async def test_chunk_with_content(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-10")
        chunk = MagicMock()
        chunk.content = "hello"
        await emitter({"event": "on_chat_model_stream", "data": {"chunk": chunk}})
        assert emitter._stream_buffer == ["hello"]

    @pytest.mark.asyncio
    async def test_chunk_without_content_attr(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-11")
        await emitter({"event": "on_chat_model_stream", "data": {"chunk": "string"}})
        assert emitter._stream_buffer == []

    @pytest.mark.asyncio
    async def test_chunk_with_empty_content(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-12")
        chunk = MagicMock()
        chunk.content = ""
        await emitter({"event": "on_chat_model_stream", "data": {"chunk": chunk}})
        assert emitter._stream_buffer == []

    @pytest.mark.asyncio
    async def test_no_chunk_in_data(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-13")
        await emitter({"event": "on_chat_model_stream", "data": {}})
        assert emitter._stream_buffer == []

    @pytest.mark.asyncio
    async def test_chunk_is_none(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-14")
        await emitter({"event": "on_chat_model_stream", "data": {"chunk": None}})
        assert emitter._stream_buffer == []


@pytest.mark.requirement("REQ-RUN-002")
class TestOnChatModelEnd:
    """Tests for on_chat_model_end event."""

    @pytest.mark.asyncio
    async def test_flushes_buffers(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-15")
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock),
            patch("streaming.emitter.save_message", new_callable=AsyncMock),
        ):
            emitter._stream_buffer = ["final content"]
            emitter._thinking_buffer = ["final thinking"]
            await emitter({"event": "on_chat_model_end", "data": {}})
            assert emitter._stream_buffer == []
            assert emitter._thinking_buffer == []


@pytest.mark.requirement("REQ-RUN-002")
class TestOnChainEnd:
    """Tests for on_chain_end event."""

    @pytest.mark.asyncio
    async def test_langgraph_flushes(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-16")
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock),
            patch("streaming.emitter.save_message", new_callable=AsyncMock),
        ):
            emitter._stream_buffer = ["chain output"]
            await emitter({"event": "on_chain_end", "name": "LangGraph", "data": {}})
            assert emitter._stream_buffer == []

    @pytest.mark.asyncio
    async def test_non_langgraph_skips(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-17")
        emitter._stream_buffer = ["keep"]
        await emitter({"event": "on_chain_end", "name": "SomeOther", "data": {}})
        assert emitter._stream_buffer == ["keep"]

    @pytest.mark.asyncio
    async def test_missing_name_skips(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-18")
        emitter._stream_buffer = ["keep"]
        await emitter({"event": "on_chain_end", "data": {}})
        assert emitter._stream_buffer == ["keep"]


@pytest.mark.requirement("REQ-RUN-002")
class TestOnThinkingNodes:
    """Tests for on_thinking_nodes event."""

    @pytest.mark.asyncio
    async def test_emits_thinking_nodes_via_event(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-19")
        nodes = [{"title": "Step 1"}]
        await emitter({"event": "on_thinking_nodes", "data": {"nodes": nodes}})
        assert emitter._pending_thinking_nodes == [{"title": "Step 1"}]

    @pytest.mark.asyncio
    async def test_empty_nodes_skips(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-20")
        await emitter({"event": "on_thinking_nodes", "data": {"nodes": []}})
        assert emitter._pending_thinking_nodes is None


@pytest.mark.requirement("REQ-RUN-002")
class TestOnToolComplete:
    """Tests for on_tool_complete event."""

    @pytest.mark.asyncio
    async def test_success_status(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-21")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter({"event": "on_tool_complete", "data": {"toolName": "search", "status": "success"}})
            mock_pub.assert_awaited_once()
            payload = mock_pub.await_args[0][1]
            assert payload["type"] == "tool_complete"
            assert "成功" in payload["node"]["content"]

    @pytest.mark.asyncio
    async def test_failure_status(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-22")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter({"event": "on_tool_complete", "data": {"toolName": "calc", "status": "error"}})
            payload = mock_pub.await_args[0][1]
            assert "失败" in payload["node"]["content"]

    @pytest.mark.asyncio
    async def test_missing_fields_uses_defaults(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-23")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter({"event": "on_tool_complete", "data": {}})
            payload = mock_pub.await_args[0][1]
            assert payload["node"]["toolName"] == ""
            assert payload["node"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_publish_failure_handled(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-24")
        with patch("streaming.emitter.publish_run_message", side_effect=Exception("fail")):
            # Should not raise
            await emitter({"event": "on_tool_complete", "data": {"toolName": "x", "status": "success"}})


@pytest.mark.requirement("REQ-RUN-002")
class TestOnClientAction:
    """Tests for on_client_action event."""

    @pytest.mark.asyncio
    async def test_publishes_action(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-25")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter({"event": "on_client_action", "data": {"action": {"type": "scroll"}}})
            mock_pub.assert_awaited_once_with(
                "run-25",
                {"type": "client_action", "agent_name": "Agent", "action": {"type": "scroll"}},
            )


@pytest.mark.requirement("REQ-RUN-002")
class TestOnToolResults:
    """Tests for on_tool_results event."""

    @pytest.mark.asyncio
    async def test_valid_tool_results(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-26")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter({
                "event": "on_tool_results",
                "data": {
                    "tool_name": "search",
                    "tool_call_id": "call-1",
                    "references": [{"id": "r1"}],
                },
            })
            mock_pub.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_refs_skips(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-27")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter({
                "event": "on_tool_results",
                "data": {"tool_name": "search", "tool_call_id": "c1", "references": []},
            })
            mock_pub.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_empty_tool_name_skips(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-28")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter({
                "event": "on_tool_results",
                "data": {"tool_name": "", "tool_call_id": "c1", "references": [{"id": "r1"}]},
            })
            mock_pub.assert_not_awaited()


@pytest.mark.requirement("REQ-RUN-002")
class TestOnToolStart:
    """Tool start events are emitted by the graph as on_custom_thinking."""

    @pytest.mark.asyncio
    async def test_emits_tool_thought(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-29")
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub,
            patch("streaming.emitter.save_message", new_callable=AsyncMock),
        ):
            await emitter({
                "event": "on_custom_thinking",
                "data": {"content": "search({\"query\": \"test\"})"},
            })
            payload = mock_pub.await_args[0][1]
            assert payload["type"] == "thinking_stream"
            assert "search" in payload["content"]
            # Thinking is not a saved message — index must stay 0.
            assert emitter._message_index == 0

    @pytest.mark.asyncio
    async def test_long_input_truncated(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-30")
        long_input = "x" * 300
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub,
            patch("streaming.emitter.save_message", new_callable=AsyncMock),
        ):
            await emitter({
                "event": "on_custom_thinking",
                "data": {"content": f"tool({long_input})"},
            })
            payload = mock_pub.await_args[0][1]
            assert payload["type"] == "thinking_stream"
            # Buffer overflows drop oldest chunks but the latest stays intact.
            assert payload["content"].endswith(")")


@pytest.mark.requirement("REQ-RUN-002")
class TestOnToolEnd:
    """Tool result events are emitted by the graph as on_custom_thinking."""

    @pytest.mark.asyncio
    async def test_emits_tool_result_thought(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-31")
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub,
            patch("streaming.emitter.save_message", new_callable=AsyncMock),
        ):
            await emitter({
                "event": "on_custom_thinking",
                "data": {"content": "[result] search → search results here"},
            })
            payload = mock_pub.await_args[0][1]
            assert payload["type"] == "thinking_stream"
            assert "[result]" in payload["content"]
            assert emitter._message_index == 0

    @pytest.mark.asyncio
    async def test_long_output_truncated(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-32")
        long_output = "y" * 600
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub,
            patch("streaming.emitter.save_message", new_callable=AsyncMock),
        ):
            await emitter({
                "event": "on_custom_thinking",
                "data": {"content": f"[result] mytool → {long_output}"},
            })
            payload = mock_pub.await_args[0][1]
            assert payload["type"] == "thinking_stream"
            # Thinking is streamed verbatim (no truncation) — the full content
            # is published so the frontend receives the complete tool result.
            assert payload["content"] == f"[result] mytool → {long_output}"


@pytest.mark.requirement("REQ-RUN-002")
class TestEmitBalanceWarning:
    """Tests for emit_balance_warning."""

    @pytest.mark.asyncio
    async def test_default_message(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-33")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter.emit_balance_warning()
            payload = mock_pub.await_args[0][1]
            assert payload["type"] == "balance_warning"
            assert payload["agent_name"] == "System"
            assert "余额" in payload["content"]

    @pytest.mark.asyncio
    async def test_custom_message(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-34")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter.emit_balance_warning("custom warning")
            payload = mock_pub.await_args[0][1]
            assert payload["content"] == "custom warning"


@pytest.mark.requirement("REQ-RUN-002")
class TestEmitThinkingNodes:
    """Tests for emit_thinking_nodes logic."""

    def test_first_call_sets_nodes(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-35")
        emitter.emit_thinking_nodes([{"a": 1}, {"b": 2}])
        assert emitter._pending_thinking_nodes == [{"a": 1}, {"b": 2}]

    def test_subsequent_calls_append(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-36")
        emitter._pending_thinking_nodes = [{"a": 1}]
        emitter.emit_thinking_nodes([{"b": 2}])
        assert len(emitter._pending_thinking_nodes) == 2

    def test_caps_at_20(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-37")
        emitter._pending_thinking_nodes = [{"i": i} for i in range(15)]
        emitter.emit_thinking_nodes([{"i": i} for i in range(15, 30)])
        assert len(emitter._pending_thinking_nodes) == 20
        assert emitter._pending_thinking_nodes[-1] == {"i": 29}

    def test_first_call_caps_at_20(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-38")
        emitter.emit_thinking_nodes([{"i": i} for i in range(25)])
        assert len(emitter._pending_thinking_nodes) == 20


@pytest.mark.requirement("REQ-RUN-002")
class TestFlushBuffers:
    """Tests for _flush_buffers internal method."""

    @pytest.mark.asyncio
    async def test_stream_only_publishes_message_and_saves(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-39")
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub,
            patch("streaming.emitter.save_message", new_callable=AsyncMock) as mock_save,
        ):
            emitter._stream_buffer = ["hello", " ", "world"]
            await emitter._flush_buffers()
            assert emitter._message_index == 1
            mock_pub.assert_awaited_once()
            msg_payload = mock_pub.await_args[0][1]
            assert msg_payload["type"] == "message"
            assert msg_payload["content"] == "hello world"
            assert msg_payload["round_number"] == 1
            mock_save.assert_awaited_once_with(
                run_id="run-39",
                role="Agent",
                agent_name="Agent",
                content="hello world",
                thinking="",
                round_number=1,
                sources=[],
            )

    @pytest.mark.asyncio
    async def test_thinking_only_publishes_thinking_done(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-40")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            emitter._thinking_buffer = ["reasoning"]
            await emitter._flush_buffers()
            # Should publish thinking_done
            calls = [c for c in mock_pub.await_args_list if c[0][1].get("type") == "thinking_done"]
            assert len(calls) == 1
            assert calls[0][0][1]["thinking"] == "reasoning"

    @pytest.mark.asyncio
    async def test_both_buffers_flushed(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-41")
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub,
            patch("streaming.emitter.save_message", new_callable=AsyncMock),
        ):
            emitter._stream_buffer = ["content"]
            emitter._thinking_buffer = ["thought"]
            await emitter._flush_buffers()
            # Two publish calls: message + thinking_done
            assert mock_pub.await_count == 2
            types = [c[0][1]["type"] for c in mock_pub.await_args_list]
            assert "message" in types
            assert "thinking_done" in types

    @pytest.mark.asyncio
    async def test_thinking_done_with_pending_nodes(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-42")
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub,
            patch("streaming.emitter.save_message", new_callable=AsyncMock),
        ):
            emitter._thinking_buffer = ["thought"]
            emitter._pending_thinking_nodes = [{"title": "Step 1"}]
            await emitter._flush_buffers()
            thinking_done_call = [c for c in mock_pub.await_args_list if c[0][1].get("type") == "thinking_done"]
            assert len(thinking_done_call) == 1
            assert thinking_done_call[0][0][1]["nodes"] == [{"title": "Step 1"}]
            assert emitter._pending_thinking_nodes is None

    @pytest.mark.asyncio
    async def test_thinking_done_without_nodes_no_nodes_key(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-43")
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub,
            patch("streaming.emitter.save_message", new_callable=AsyncMock),
        ):
            emitter._thinking_buffer = ["thought"]
            await emitter._flush_buffers()
            thinking_done_call = [c for c in mock_pub.await_args_list if c[0][1].get("type") == "thinking_done"]
            assert "nodes" not in thinking_done_call[0][0][1]

    @pytest.mark.asyncio
    async def test_empty_thinking_buffer_stripped(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-44")
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub,
            patch("streaming.emitter.save_message", new_callable=AsyncMock),
        ):
            emitter._thinking_buffer = ["  ", "  "]
            await emitter._flush_buffers()
            thinking_done_call = [c for c in mock_pub.await_args_list if c[0][1].get("type") == "thinking_done"]
            assert len(thinking_done_call) == 0

    @pytest.mark.asyncio
    async def test_publish_message_failure_handled(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-45")
        with (
            patch("streaming.emitter.publish_run_message", side_effect=Exception("fail")),
            patch("streaming.emitter.save_message", new_callable=AsyncMock),
        ):
            emitter._stream_buffer = ["content"]
            # Should not raise
            await emitter._flush_buffers()

    @pytest.mark.asyncio
    async def test_publish_thinking_done_failure_handled(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-46")
        call_count = 0

        async def _mock_publish(run_id, payload):
            nonlocal call_count
            call_count += 1
            if payload.get("type") == "thinking_done":
                raise Exception("thinking publish fail")

        with (
            patch("streaming.emitter.publish_run_message", side_effect=_mock_publish),
            patch("streaming.emitter.save_message", new_callable=AsyncMock),
        ):
            emitter._thinking_buffer = ["thought"]
            emitter._stream_buffer = ["content"]
            # Should not raise
            await emitter._flush_buffers()

    @pytest.mark.asyncio
    async def test_message_index_increments(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-47")
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock),
            patch("streaming.emitter.save_message", new_callable=AsyncMock),
        ):
            emitter._stream_buffer = ["first"]
            await emitter._flush_buffers()
            assert emitter._message_index == 1
            emitter._stream_buffer = ["second"]
            await emitter._flush_buffers()
            assert emitter._message_index == 2


@pytest.mark.requirement("REQ-RUN-002")
class TestEmitMethod:
    """Tests for _emit internal method."""

    @pytest.mark.asyncio
    async def test_publishes_and_saves_message(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-48")
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub,
            patch("streaming.emitter.save_message", new_callable=AsyncMock) as mock_save,
        ):
            await emitter._emit("Agent", "tool output")
            assert emitter._message_index == 1
            payload = mock_pub.await_args[0][1]
            assert payload["type"] == "message"
            assert payload["content"] == "tool output"
            assert payload["round_number"] == 1
            mock_save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_with_thinking_parameter(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-49")
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub,
            patch("streaming.emitter.save_message", new_callable=AsyncMock),
        ):
            await emitter._emit("Agent", "output", thinking="my thinking")
            payload = mock_pub.await_args[0][1]
            assert payload["thinking"] == "my thinking"

    @pytest.mark.asyncio
    async def test_uses_pending_thinking_if_no_explicit(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-50")
        emitter._pending_thinking = "stored thinking"
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub,
            patch("streaming.emitter.save_message", new_callable=AsyncMock),
        ):
            await emitter._emit("Agent", "output")
            payload = mock_pub.await_args[0][1]
            assert payload["thinking"] == "stored thinking"
            assert emitter._pending_thinking is None

    @pytest.mark.asyncio
    async def test_explicit_thinking_overrides_pending(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-51")
        emitter._pending_thinking = "pending"
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub,
            patch("streaming.emitter.save_message", new_callable=AsyncMock),
        ):
            await emitter._emit("Agent", "output", thinking="explicit")
            payload = mock_pub.await_args[0][1]
            assert payload["thinking"] == "explicit"
            assert emitter._pending_thinking == "pending"

    @pytest.mark.asyncio
    async def test_non_message_type_skips_save(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-52")
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock),
            patch("streaming.emitter.save_message", new_callable=AsyncMock) as mock_save,
        ):
            await emitter._emit("Agent", "output", msg_type="stream")
            mock_save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_publish_failure_handled(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-53")
        with patch("streaming.emitter.publish_run_message", side_effect=Exception("fail")):
            with patch("streaming.emitter.save_message", new_callable=AsyncMock) as mock_save:
                await emitter._emit("Agent", "output")
                mock_save.assert_not_awaited()


@pytest.mark.requirement("REQ-RUN-002")
class TestUnknownEvents:
    """Tests for unknown/unrecognized event types."""

    @pytest.mark.asyncio
    async def test_unknown_event_ignored(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-54")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter({"event": "on_unknown_event", "data": {"key": "val"}})
            mock_pub.assert_not_awaited()
            assert emitter._message_index == 0


@pytest.mark.requirement("REQ-RUN-002")
class TestEventWithMissingData:
    """Tests for events with missing or malformed data keys."""

    @pytest.mark.asyncio
    async def test_on_custom_token_missing_event_key(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-55")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter({"data": {"content": "hello"}})
            mock_pub.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_on_tool_start_is_noop(self):
        """on_tool_start is handled at the graph level (as on_custom_thinking);
        emitter must ignore the raw event entirely."""
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-56")
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub,
            patch("streaming.emitter.save_message", new_callable=AsyncMock) as mock_save,
        ):
            await emitter({"event": "on_tool_start", "data": {"input": "test"}})
            mock_pub.assert_not_awaited()
            mock_save.assert_not_awaited()
            assert emitter._message_index == 0

    @pytest.mark.asyncio
    async def test_on_tool_end_is_noop(self):
        """on_tool_end is handled at the graph level (as on_custom_thinking);
        emitter must ignore the raw event entirely."""
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-57")
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub,
            patch("streaming.emitter.save_message", new_callable=AsyncMock) as mock_save,
        ):
            await emitter({"event": "on_tool_end", "data": {"output": "result"}})
            mock_pub.assert_not_awaited()
            mock_save.assert_not_awaited()
            assert emitter._message_index == 0
