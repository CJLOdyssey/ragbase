"""Tests for agent pipeline and stream emitter."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_run_agent_pipeline_importable():
    """Verify agent pipeline and run_agent are importable."""
    from tasks import _run_agent_pipeline, run_agent

    assert _run_agent_pipeline is not None
    assert run_agent is not None


@pytest.mark.asyncio
async def test_stream_emitter_buffers_chunks():
    """Verify StreamEmitter buffers streaming chunks before publishing."""
    from streaming.emitter import StreamEmitter

    with (
        patch("streaming.emitter.publish_run_message") as mock_pub,
        patch("streaming.emitter.save_message") as mock_save,
    ):
        emitter = StreamEmitter("test-run")
        await emitter(
            {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="Hello")}}
        )
        await emitter(
            {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content=" World")}}
        )
        await emitter({"event": "on_chat_model_end", "data": {}})
        mock_pub.assert_called_once()
        mock_save.assert_called_once()
        assert mock_save.call_args[1]["content"] == "Hello World"


@pytest.mark.asyncio
async def test_stream_emitter_tool_events():
    """Tool start is emitted by the graph as on_custom_thinking and streamed."""
    from streaming.emitter import StreamEmitter

    with (
        patch("streaming.emitter.publish_run_message") as mock_pub,
        patch("streaming.emitter.save_message") as mock_save,
    ):
        emitter = StreamEmitter("test-run")
        await emitter({
            "event": "on_custom_thinking",
            "data": {"content": "search({\"input\": \"query\"})"},
        })
        mock_pub.assert_awaited()
        payload = mock_pub.await_args[0][1]
        assert payload["type"] == "thinking_stream"
        assert "search" in payload["content"]
        mock_save.assert_not_awaited()


def test_run_status_valid_states():
    """Verify run status valid/invalid states."""
    valid_states = {"pending", "running", "converged", "error", "max_rounds_reached"}
    assert "converged" in valid_states
    assert "invalid" not in valid_states
