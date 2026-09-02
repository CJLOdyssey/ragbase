"""Tests for backend.tasks.prefix_completion — stream_prefix_completion."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


def _mock_stream(lines: list[str], status: int = 200) -> AsyncMock:
    """httpx.AsyncClient 流式响应 mock（aiter_lines 依次产出 SSE 行）。"""
    mock_response = AsyncMock()
    mock_response.status_code = status
    if status == 200:
        mock_response.aiter_lines = MagicMock(return_value=async_iter(lines))
        mock_response.raise_for_status = MagicMock()
    else:
        mock_response.aread = AsyncMock(return_value=b"Internal Server Error")
        mock_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
            f"{status}", request=MagicMock(), response=mock_response,
        ))

    mock_stream_ctx = AsyncMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_client = AsyncMock()
    mock_client.stream = MagicMock(return_value=mock_stream_ctx)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


async def async_iter(items):
    """Create an async iterator from a list."""
    for item in items:
        yield item


class TestStreamPrefixCompletion:

    @patch("tasks.prefix_completion.publish_run_message", new_callable=AsyncMock)
    async def test_success_with_content(self, mock_publish):
        """Happy path: stream returns content tokens, each published as stream."""
        from tasks.prefix_completion import stream_prefix_completion

        chunk1 = json.dumps({"choices": [{"delta": {"content": "Hello"}}]})
        chunk2 = json.dumps({"choices": [{"delta": {"content": " world"}}]})
        lines = [f"data: {chunk1}", f"data: {chunk2}", "data: [DONE]"]

        with patch("tasks.prefix_completion.httpx.AsyncClient", return_value=_mock_stream(lines)):
            content, thinking = await stream_prefix_completion(
                "http://test.com/chat", {}, {"model": "test"}, "run-1"
            )

        assert content == "Hello world"
        assert thinking == []
        # 每个 token 块发布 stream 事件（前端实时渲染）。
        payloads = [c[0][1] for c in mock_publish.await_args_list]
        assert payloads == [
            {"type": "stream", "agent_name": "Agent", "content": "Hello"},
            {"type": "stream", "agent_name": "Agent", "content": " world"},
        ]

    @patch("tasks.prefix_completion.publish_run_message", new_callable=AsyncMock)
    async def test_success_with_thinking(self, mock_publish):
        """Stream returns both reasoning_content and content."""
        from tasks.prefix_completion import stream_prefix_completion

        chunk1 = json.dumps({"choices": [{"delta": {"reasoning_content": "thinking...", "content": ""}}]})
        chunk2 = json.dumps({"choices": [{"delta": {"content": "answer"}}]})
        lines = [f"data: {chunk1}", f"data: {chunk2}", "data: [DONE]"]

        with patch("tasks.prefix_completion.httpx.AsyncClient", return_value=_mock_stream(lines)):
            content, thinking = await stream_prefix_completion(
                "http://test.com/chat", {}, {"model": "test"}, "run-1"
            )

        assert content == "answer"
        assert "thinking..." in thinking
        # reasoning 块发 thinking_stream，正文块发 stream。
        payloads = [c[0][1] for c in mock_publish.await_args_list]
        assert payloads == [
            {"type": "thinking_stream", "agent_name": "Agent", "content": "thinking..."},
            {"type": "stream", "agent_name": "Agent", "content": "answer"},
        ]

    @patch("tasks.prefix_completion.publish_run_message", new_callable=AsyncMock)
    async def test_non_200_raises(self, mock_publish):
        """Non-200 status raises HTTPStatusError."""
        from tasks.prefix_completion import stream_prefix_completion

        with patch("tasks.prefix_completion.httpx.AsyncClient", return_value=_mock_stream([], status=500)):
            with pytest.raises(httpx.HTTPStatusError):
                await stream_prefix_completion(
                    "http://test.com/chat", {}, {"model": "test"}, "run-1"
                )
        mock_publish.assert_not_awaited()

    @patch("tasks.prefix_completion.publish_run_message", new_callable=AsyncMock)
    async def test_empty_and_non_data_lines_skipped(self, mock_publish):
        """Lines not starting with 'data: ' are skipped."""
        from tasks.prefix_completion import stream_prefix_completion

        lines = ["", "event: ping", "data: [DONE]"]

        with patch("tasks.prefix_completion.httpx.AsyncClient", return_value=_mock_stream(lines)):
            content, thinking = await stream_prefix_completion(
                "http://test.com/chat", {}, {"model": "test"}, "run-1"
            )

        assert content == ""
        assert thinking == []
        mock_publish.assert_not_awaited()

    @patch("tasks.prefix_completion.publish_run_message", new_callable=AsyncMock)
    async def test_invalid_json_chunk_skipped(self, mock_publish):
        """Invalid JSON in data line is skipped."""
        from tasks.prefix_completion import stream_prefix_completion

        lines = ["data: not-valid-json{", "data: [DONE]"]

        with patch("tasks.prefix_completion.httpx.AsyncClient", return_value=_mock_stream(lines)):
            content, thinking = await stream_prefix_completion(
                "http://test.com/chat", {}, {"model": "test"}, "run-1"
            )

        assert content == ""
        mock_publish.assert_not_awaited()

    @patch("tasks.prefix_completion.publish_run_message", new_callable=AsyncMock)
    async def test_empty_choices_skipped(self, mock_publish):
        """Chunks with empty choices list are skipped."""
        from tasks.prefix_completion import stream_prefix_completion

        chunk = json.dumps({"choices": []})
        lines = [f"data: {chunk}", "data: [DONE]"]

        with patch("tasks.prefix_completion.httpx.AsyncClient", return_value=_mock_stream(lines)):
            content, _ = await stream_prefix_completion(
                "http://test.com/chat", {}, {"model": "test"}, "run-1"
            )

        assert content == ""
        mock_publish.assert_not_awaited()


class TestPrefixCompletionErrorHandling:

    @patch("tasks.prefix_completion.publish_run_message", new_callable=AsyncMock)
    async def test_no_content_in_delta_skipped(self, mock_publish):
        """Delta with empty content and no reasoning is skipped."""
        from tasks.prefix_completion import stream_prefix_completion

        chunk = json.dumps({"choices": [{"delta": {}}]})
        lines = [f"data: {chunk}", "data: [DONE]"]

        with patch("tasks.prefix_completion.httpx.AsyncClient", return_value=_mock_stream(lines)):
            content, thinking = await stream_prefix_completion(
                "http://test.com/chat", {}, {"model": "test"}, "run-1"
            )

        assert content == ""
        assert thinking == []
        mock_publish.assert_not_awaited()
