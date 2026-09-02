"""Unit tests for streaming/emitter.py (StreamEmitter edge cases)."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.requirement("REQ-RUN-002")
class TestStreamingEdgeCases:
    """Test StreamEmitter edge cases: empty data, None values, error handling."""

    def test_import(self):
        from streaming.emitter import StreamEmitter

        assert StreamEmitter is not None

    def test_init_sets_run_id(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-test")
        assert emitter._run_id == "run-test"
        assert emitter._message_index == 0
        assert emitter._stream_buffer == []
        assert emitter._thinking_buffer == []

    @pytest.mark.asyncio
    async def test_call_with_empty_event(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-empty")
        await emitter({})
        assert emitter._message_index == 0

    @pytest.mark.asyncio
    async def test_call_with_none_data(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-none")
        await emitter({"event": "on_custom_token", "data": None})
        assert emitter._stream_buffer == []

    @pytest.mark.asyncio
    async def test_call_with_empty_data(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-emptydata")
        await emitter({"event": "on_custom_token", "data": {}})
        assert emitter._stream_buffer == []

    @pytest.mark.asyncio
    async def test_on_custom_token_appends_to_buffer(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-token")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter({"event": "on_custom_token", "data": {"content": "hello"}})
            assert emitter._stream_buffer == ["hello"]
            mock_pub.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_on_custom_token_empty_content(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-emptycontent")
        with patch("streaming.emitter.publish_run_message") as mock_pub:
            await emitter({"event": "on_custom_token", "data": {"content": ""}})
            assert emitter._stream_buffer == []
            mock_pub.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_custom_thinking_appends(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-think")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter({"event": "on_custom_thinking", "data": {"content": "thinking..."}})
            assert emitter._thinking_buffer == ["thinking..."]
            mock_pub.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_on_custom_thinking_empty_content(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-thinkempty")
        with patch("streaming.emitter.publish_run_message") as mock_pub:
            await emitter({"event": "on_custom_thinking", "data": {"content": ""}})
            assert emitter._thinking_buffer == []
            mock_pub.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_node_end_flushes_buffers(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-flush")
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock),
            patch("streaming.emitter.save_message", new_callable=AsyncMock),
        ):
            emitter._stream_buffer = ["hello ", "world"]
            emitter._thinking_buffer = ["think"]
            await emitter({"event": "on_node_end", "data": {}})
            assert emitter._stream_buffer == []
            assert emitter._thinking_buffer == []

    @pytest.mark.asyncio
    async def test_on_chat_model_stream_no_chunk(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-nostream")
        await emitter({"event": "on_chat_model_stream", "data": {}})
        assert emitter._stream_buffer == []

    @pytest.mark.asyncio
    async def test_on_chat_model_end_flushes(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-chatend")
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock),
            patch("streaming.emitter.save_message", new_callable=AsyncMock),
        ):
            emitter._stream_buffer = ["final"]
            await emitter({"event": "on_chat_model_end", "data": {}})
            assert emitter._stream_buffer == []

    @pytest.mark.asyncio
    async def test_on_chain_end_langgraph_flushes(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-chain")
        with (
            patch("streaming.emitter.publish_run_message", new_callable=AsyncMock),
            patch("streaming.emitter.save_message", new_callable=AsyncMock),
        ):
            emitter._stream_buffer = ["chain-output"]
            await emitter({"event": "on_chain_end", "name": "LangGraph", "data": {}})
            assert emitter._stream_buffer == []

    @pytest.mark.asyncio
    async def test_on_chain_end_non_langgraph_skips(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-chain-skip")
        emitter._stream_buffer = ["no-flush"]
        await emitter({"event": "on_chain_end", "name": "OtherGraph", "data": {}})
        assert emitter._stream_buffer == ["no-flush"]

    @pytest.mark.asyncio
    async def test_on_tool_results_with_empty_references(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-toolempty")
        with patch("streaming.emitter.publish_run_message") as mock_pub:
            await emitter({
                "event": "on_tool_results",
                "data": {"tool_name": "search", "tool_call_id": "call-1", "references": []},
            })
            mock_pub.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_tool_results_without_tool_name(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-toolnoname")
        with patch("streaming.emitter.publish_run_message") as mock_pub:
            await emitter({
                "event": "on_tool_results",
                "data": {"tool_name": "", "tool_call_id": "call-1", "references": [{"id": "1"}]},
            })
            mock_pub.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_tool_results_with_valid_data(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-toolvalid")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter({
                "event": "on_tool_results",
                "data": {
                    "tool_name": "search",
                    "tool_call_id": "call-1",
                    "references": [{"id": "ref-1", "content": "result"}],
                },
            })
            mock_pub.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_emit_balance_warning_default_message(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-balance")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            await emitter.emit_balance_warning()
            call_kwargs = mock_pub.await_args[0][1]
            assert call_kwargs["type"] == "balance_warning"

    @pytest.mark.asyncio
    async def test_emit_tool_results(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-toolres")
        with patch("streaming.emitter.publish_run_message", new_callable=AsyncMock) as mock_pub:
            refs = [{"id": "r1", "content": "data"}]
            await emitter.emit_tool_results("search", "call-1", refs)
            mock_pub.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_emit_thinking_nodes(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-thinknodes")
        nodes = [{"title": "Step 1", "content": "thinking..."}]
        emitter.emit_thinking_nodes(nodes)
        assert len(emitter._pending_thinking_nodes) == 1

    @pytest.mark.asyncio
    async def test_emit_thinking_nodes_caps_at_20(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-thinkcap")
        emitter._pending_thinking_nodes = [{"i": i} for i in range(15)]
        nodes = [{"i": i} for i in range(15, 30)]
        emitter.emit_thinking_nodes(nodes)
        assert len(emitter._pending_thinking_nodes) == 20

    @pytest.mark.asyncio
    async def test_emit_thinking_nodes_appends_to_existing(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-thinkappend")
        emitter._pending_thinking_nodes = [{"title": "first"}]
        emitter.emit_thinking_nodes([{"title": "second"}])
        assert len(emitter._pending_thinking_nodes) == 2

    @pytest.mark.asyncio
    async def test_publish_failure_on_stream_chunk(self):
        from streaming.emitter import StreamEmitter

        emitter = StreamEmitter("run-pubfail")
        with patch("streaming.emitter.publish_run_message", side_effect=Exception("Redis down")):
            await emitter({"event": "on_custom_token", "data": {"content": "hello"}})
            assert emitter._stream_buffer == ["hello"]


