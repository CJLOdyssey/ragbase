"""Comprehensive tests for backend/streaming/llm_stream.py — all functions and edge cases."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

# ── Mock SSE helpers ────────────────────────────────────────────────────────

class _MockStreamCtx:
    def __init__(self, sse_lines, status_code=200):
        self.status_code = status_code
        self._sse_lines = sse_lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return None

    async def aiter_lines(self):
        for line in self._sse_lines:
            yield line

    async def aread(self):
        return b"error body"

    def raise_for_status(self):
        if self.status_code != 200:
            raise httpx.HTTPStatusError(
                "error", request=MagicMock(), response=MagicMock(status_code=self.status_code)
            )


class _MockClientCtx:
    def __init__(self, sse_lines, status_code=200, raise_error=False):
        self._sse_lines = sse_lines
        self._status_code = status_code
        self._raise_error = raise_error

    def stream(self, method, url, headers=None, json=None):
        if self._raise_error:
            raise httpx.ConnectError("connection refused")
        return _MockStreamCtx(self._sse_lines, self._status_code)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return None


# ── Tests: convert_messages_to_api ──────────────────────────────────────────


class TestConvertMessagesToApi:
    def test_system_message(self):
        from streaming.llm_stream import convert_messages_to_api

        result = convert_messages_to_api([SystemMessage(content="sys")])
        assert result == [{"role": "system", "content": "sys"}]

    def test_human_message(self):
        from streaming.llm_stream import convert_messages_to_api

        result = convert_messages_to_api([HumanMessage(content="hi")])
        assert result == [{"role": "user", "content": "hi"}]

    def test_ai_message_without_tool_calls(self):
        from streaming.llm_stream import convert_messages_to_api

        result = convert_messages_to_api([AIMessage(content="reply")])
        assert result == [{"role": "assistant", "content": "reply"}]
        assert "tool_calls" not in result[0]

    def test_ai_message_with_tool_calls(self):
        from streaming.llm_stream import convert_messages_to_api

        msg = AIMessage(
            content="calling tool",
            tool_calls=[{"id": "c1", "name": "search", "args": {"q": "test"}}],
        )
        result = convert_messages_to_api([msg])
        assert result[0]["tool_calls"][0]["id"] == "c1"
        assert result[0]["tool_calls"][0]["function"]["name"] == "search"
        assert json.loads(result[0]["tool_calls"][0]["function"]["arguments"]) == {"q": "test"}

    def test_tool_message(self):
        from streaming.llm_stream import convert_messages_to_api

        result = convert_messages_to_api([ToolMessage(content="done", tool_call_id="c1")])
        assert result[0]["role"] == "tool"
        assert result[0]["tool_call_id"] == "c1"

    def test_empty_list(self):
        from streaming.llm_stream import convert_messages_to_api

        assert convert_messages_to_api([]) == []

    def test_mixed_order(self):
        from streaming.llm_stream import convert_messages_to_api

        msgs = [
            SystemMessage(content="s"),
            HumanMessage(content="h"),
            AIMessage(content="a", tool_calls=[{"id": "c1", "name": "t", "args": {}}]),
            ToolMessage(content="r", tool_call_id="c1"),
        ]
        result = convert_messages_to_api(msgs)
        assert [m["role"] for m in result] == ["system", "user", "assistant", "tool"]

    def test_ai_message_multiple_tool_calls(self):
        from streaming.llm_stream import convert_messages_to_api

        msg = AIMessage(
            content="multi",
            tool_calls=[
                {"id": "c1", "name": "tool_a", "args": {"x": 1}},
                {"id": "c2", "name": "tool_b", "args": {"y": 2}},
            ],
        )
        result = convert_messages_to_api([msg])
        assert len(result[0]["tool_calls"]) == 2


# ── Tests: build_llm_request_body ───────────────────────────────────────────


class TestBuildLlmRequestBody:
    def test_deepseek_default_url(self):
        from streaming.llm_stream import build_llm_request_body

        url, headers, body = build_llm_request_body(
            [], model="deepseek-chat", api_key="sk-test"
        )
        assert url == "https://api.deepseek.com/chat/completions"

    def test_custom_base_url(self):
        from streaming.llm_stream import build_llm_request_body

        url, _, _ = build_llm_request_body(
            [], model="gpt-4", api_key="sk-xxx", base_url="https://api.openai.com/v1"
        )
        assert url == "https://api.openai.com/v1/chat/completions"

    def test_base_url_trailing_slash_stripped(self):
        from streaming.llm_stream import build_llm_request_body

        url, _, _ = build_llm_request_body(
            [], model="m", api_key="k", base_url="https://example.com/v1/"
        )
        assert url == "https://example.com/v1/chat/completions"

    def test_auth_header(self):
        from streaming.llm_stream import build_llm_request_body

        _, headers, _ = build_llm_request_body([], model="m", api_key="sk-secret")
        assert headers["Authorization"] == "Bearer sk-secret"
        assert headers["Content-Type"] == "application/json"

    def test_body_has_stream_options(self):
        from streaming.llm_stream import build_llm_request_body

        _, _, body = build_llm_request_body([], model="m", api_key="k")
        assert body["stream"] is True
        assert body["stream_options"] == {"include_usage": True}

    def test_custom_temperature_and_max_tokens(self):
        from streaming.llm_stream import build_llm_request_body

        _, _, body = build_llm_request_body(
            [], model="m", api_key="k", temperature=0.2, max_tokens=2048
        )
        assert body["temperature"] == 0.2
        assert body["max_tokens"] == 2048

    def test_deepseek_thinking_enabled_without_tools(self):
        from streaming.llm_stream import build_llm_request_body

        _, _, body = build_llm_request_body(
            [], model="deepseek-chat", api_key="k"
        )
        assert body["thinking"] == {"type": "enabled"}

    def test_deepseek_thinking_disabled_with_tools(self):
        from streaming.llm_stream import build_llm_request_body

        tools = [{"type": "function", "function": {"name": "t", "description": "d"}}]
        _, _, body = build_llm_request_body(
            [], model="deepseek-chat", api_key="k", tool_definitions=tools
        )
        assert "thinking" not in body
        assert body["tools"] == tools
        assert body["tool_choice"] == "auto"

    def test_non_deepseek_no_thinking(self):
        from streaming.llm_stream import build_llm_request_body

        _, _, body = build_llm_request_body(
            [], model="gpt-4", api_key="k", base_url="https://api.openai.com/v1"
        )
        assert "thinking" not in body

    def test_deepseek_in_base_url(self):
        from streaming.llm_stream import build_llm_request_body

        _, _, body = build_llm_request_body(
            [], model="other-model", api_key="k",
            base_url="https://api.deepseek.com/v1"
        )
        assert body["thinking"] == {"type": "enabled"}


# ── Tests: build_tool_calls_list ────────────────────────────────────────────


class TestBuildToolCallsList:
    def test_empty_map(self):
        from streaming.llm_stream import build_tool_calls_list

        assert build_tool_calls_list({}) == []

    def test_single_tool_call(self):
        from streaming.llm_stream import build_tool_calls_list

        result = build_tool_calls_list({
            0: {"id": "c1", "name": "search", "arguments": '{"q":"hi"}'}
        })
        assert len(result) == 1
        assert result[0]["id"] == "c1"
        assert result[0]["name"] == "search"
        assert result[0]["args"] == {"q": "hi"}

    def test_multiple_sorted_by_index(self):
        from streaming.llm_stream import build_tool_calls_list

        result = build_tool_calls_list({
            2: {"id": "c3", "name": "third", "arguments": "{}"},
            0: {"id": "c1", "name": "first", "arguments": "{}"},
            1: {"id": "c2", "name": "second", "arguments": "{}"},
        })
        assert [r["id"] for r in result] == ["c1", "c2", "c3"]

    def test_empty_name_skipped(self):
        from streaming.llm_stream import build_tool_calls_list

        result = build_tool_calls_list({
            0: {"id": "c1", "name": "", "arguments": "{}"}
        })
        assert result == []

    def test_invalid_json_arguments(self):
        from streaming.llm_stream import build_tool_calls_list

        result = build_tool_calls_list({
            0: {"id": "c1", "name": "t", "arguments": "not json"}
        })
        assert result[0]["args"] == {}

    def test_empty_arguments(self):
        from streaming.llm_stream import build_tool_calls_list

        result = build_tool_calls_list({
            0: {"id": "c1", "name": "t", "arguments": ""}
        })
        assert result[0]["args"] == {}

    def test_none_arguments(self):
        from streaming.llm_stream import build_tool_calls_list

        result = build_tool_calls_list({
            0: {"id": "c1", "name": "t", "arguments": None}
        })
        assert result[0]["args"] == {}


# ── Tests: stream_llm_response ──────────────────────────────────────────────


class TestStreamLlmResponse:
    @pytest.mark.asyncio
    async def test_basic_content_stream(self):
        from streaming.llm_stream import stream_llm_response

        sse = [
            'data: {"choices":[{"delta":{"content":"Hi"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":" there"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":""},"finish_reason":"stop","usage":{"input_tokens":10,"output_tokens":5}}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse)):
            content, thinking, tc, fr, usage = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk"},
                {"model": "m", "messages": []},
            )
        assert "".join(content) == "Hi there"
        assert thinking == []
        assert tc == {}
        assert fr == "stop"

    @pytest.mark.asyncio
    async def test_reasoning_content_collected(self):
        from streaming.llm_stream import stream_llm_response

        sse = [
            'data: {"choices":[{"delta":{"reasoning_content":"Step 1"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"reasoning_content":"Step 2"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"Answer"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse)):
            content, thinking, _, fr, _ = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk"},
                {"model": "m", "messages": []},
            )
        assert "".join(thinking) == "Step 1Step 2"
        assert "".join(content) == "Answer"

    @pytest.mark.asyncio
    async def test_tool_call_deltas_collected(self):
        from streaming.llm_stream import stream_llm_response

        sse = [
            'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"c1","function":{"name":"search","arguments":""}}]},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"{\\"q\\": \\"hi\\"}"}}]},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"tool_calls":[]},"finish_reason":"tool_calls"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse)):
            content, thinking, tc, fr, usage = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk"},
                {"model": "m", "messages": []},
            )
        assert 0 in tc
        assert tc[0]["name"] == "search"
        assert tc[0]["id"] == "c1"
        assert fr == "tool_calls"

    @pytest.mark.asyncio
    async def test_tool_calls_clear_pending_content(self):
        from streaming.llm_stream import stream_llm_response

        sse = [
            'data: {"choices":[{"delta":{"content":"before tool"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"c1","function":{"name":"t","arguments":"{}"}}]},"finish_reason":"tool_calls"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse)):
            content, thinking, tc, fr, usage = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk"},
                {"model": "m", "messages": []},
                tool_definitions=[{"type": "function", "function": {"name": "t"}}],
            )
        # "before tool" should be discarded (pending_content cleared when tool_calls seen)
        assert content == []

    @pytest.mark.asyncio
    async def test_pending_content_flushed_when_no_tool_calls(self):
        from streaming.llm_stream import stream_llm_response

        sse = [
            'data: {"choices":[{"delta":{"content":"pending"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":" data"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse)):
            content, _, _, _, _ = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk"},
                {"model": "m", "messages": []},
                tool_definitions=[{"type": "function", "function": {"name": "t"}}],
            )
        assert "".join(content) == "pending data"

    @pytest.mark.asyncio
    async def test_skips_non_data_lines(self):
        from streaming.llm_stream import stream_llm_response

        sse = [
            ": comment",
            "event: custom",
            "",
            'data: {"choices":[{"delta":{"content":"ok"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse)):
            content, _, _, _, _ = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk"},
                {"model": "m", "messages": []},
            )
        assert "".join(content) == "ok"

    @pytest.mark.asyncio
    async def test_json_decode_error_skipped(self):
        from streaming.llm_stream import stream_llm_response

        sse = [
            "data: {bad json",
            'data: {"choices":[{"delta":{"content":"ok"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse)):
            content, _, _, _, _ = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk"},
                {"model": "m", "messages": []},
            )
        assert "".join(content) == "ok"

    @pytest.mark.asyncio
    async def test_empty_choices_skipped(self):
        from streaming.llm_stream import stream_llm_response

        sse = [
            'data: {"choices":[]}',
            'data: {"choices":[{"delta":{"content":"hi"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse)):
            content, _, _, _, _ = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk"},
                {"model": "m", "messages": []},
            )
        assert "".join(content) == "hi"

    @pytest.mark.asyncio
    async def test_stream_callback_content(self):
        from streaming.llm_stream import stream_llm_response

        cb = AsyncMock()
        sse = [
            'data: {"choices":[{"delta":{"content":"A"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"B"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse)):
            await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk"},
                {"model": "m", "messages": []},
                stream_cb=cb,
            )
        assert cb.await_count == 2
        cb.assert_any_call({"event": "on_custom_token", "data": {"content": "A"}})
        cb.assert_any_call({"event": "on_custom_token", "data": {"content": "B"}})

    @pytest.mark.asyncio
    async def test_stream_callback_thinking(self):
        from streaming.llm_stream import stream_llm_response

        cb = AsyncMock()
        sse = [
            'data: {"choices":[{"delta":{"reasoning_content":"think"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"ans"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse)):
            await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk"},
                {"model": "m", "messages": []},
                stream_cb=cb,
            )
        cb.assert_any_call({"event": "on_custom_thinking", "data": {"content": "think"}})

    @pytest.mark.asyncio
    async def test_http_error_raises_and_circuit_breaker(self):
        from streaming.llm_stream import stream_llm_response

        with (
            patch("httpx.AsyncClient", return_value=_MockClientCtx([], status_code=500)),
            patch("streaming.llm_stream.llm_circuit") as mock_cb,
        ):
            mock_cb.acquire = AsyncMock()
            mock_cb.record_failure = AsyncMock()
            with pytest.raises(httpx.HTTPStatusError):
                await stream_llm_response(
                    "https://api.deepseek.com/chat/completions",
                    {"Authorization": "Bearer sk"},
                    {"model": "m", "messages": []},
                )
            mock_cb.record_failure.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_connect_error_raises_and_circuit_breaker(self):
        from streaming.llm_stream import stream_llm_response

        with (
            patch("httpx.AsyncClient", return_value=_MockClientCtx([], raise_error=True)),
            patch("streaming.llm_stream.llm_circuit") as mock_cb,
        ):
            mock_cb.acquire = AsyncMock()
            mock_cb.record_failure = AsyncMock()
            with pytest.raises(httpx.ConnectError):
                await stream_llm_response(
                    "https://api.deepseek.com/chat/completions",
                    {"Authorization": "Bearer sk"},
                    {"model": "m", "messages": []},
                )
            mock_cb.record_failure.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_success_calls_circuit_breaker_on_success(self):
        from streaming.llm_stream import stream_llm_response

        sse = [
            'data: {"choices":[{"delta":{"content":"ok"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]
        with (
            patch("httpx.AsyncClient", return_value=_MockClientCtx(sse)),
            patch("streaming.llm_stream.llm_circuit") as mock_cb,
        ):
            mock_cb.acquire = AsyncMock()
            mock_cb.record_success = AsyncMock()
            await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk"},
                {"model": "m", "messages": []},
            )
            mock_cb.record_success.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_rejects(self):
        from core.infra.circuit_breaker import CircuitBreakerOpenError
        from streaming.llm_stream import stream_llm_response

        with patch("streaming.llm_stream.llm_circuit") as mock_cb:
            mock_cb.acquire = AsyncMock(side_effect=CircuitBreakerOpenError("open"))
            with pytest.raises(CircuitBreakerOpenError):
                await stream_llm_response(
                    "https://api.deepseek.com/chat/completions",
                    {"Authorization": "Bearer sk"},
                    {"model": "m", "messages": []},
                )

    @pytest.mark.asyncio
    async def test_usage_info_from_finish_chunk(self):
        from streaming.llm_stream import stream_llm_response

        sse = [
            'data: {"choices":[{"delta":{"content":"done"},"finish_reason":"stop"}],"usage":{"input_tokens":100,"output_tokens":50}}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse)):
            _, _, _, fr, usage = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk"},
                {"model": "m", "messages": []},
            )
        assert fr == "stop"
        assert usage.get("input_tokens") == 100

    @pytest.mark.asyncio
    async def test_no_content_no_thinking_no_tools(self):
        from streaming.llm_stream import stream_llm_response

        sse = [
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse)):
            content, thinking, tc, fr, usage = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk"},
                {"model": "m", "messages": []},
            )
        assert content == []
        assert thinking == []
        assert tc == {}

    @pytest.mark.asyncio
    async def test_multiple_tool_call_indices(self):
        from streaming.llm_stream import stream_llm_response

        sse = [
            'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"c1","function":{"name":"t1","arguments":"{}"}},{"index":1,"id":"c2","function":{"name":"t2","arguments":"{}"}}]},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{},"finish_reason":"tool_calls"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse)):
            _, _, tc, fr, _ = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk"},
                {"model": "m", "messages": []},
            )
        assert len(tc) == 2
        assert tc[0]["name"] == "t1"
        assert tc[1]["name"] == "t2"

    @pytest.mark.asyncio
    async def test_thinking_then_content_marks_thinking_flushed(self):
        from streaming.llm_stream import stream_llm_response

        sse = [
            'data: {"choices":[{"delta":{"reasoning_content":"think"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"answer"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":" more"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse)):
            content, thinking, _, _, _ = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk"},
                {"model": "m", "messages": []},
            )
        assert "".join(content) == "answer more"
        assert "".join(thinking) == "think"

    @pytest.mark.asyncio
    async def test_stream_callback_exception_suppressed_for_thinking(self):
        from streaming.llm_stream import stream_llm_response

        # Only the reasoning_content callback is wrapped in contextlib.suppress;
        # content callbacks propagate. Test that reasoning callback exception is suppressed.
        call_count = 0

        async def _cb(event):
            nonlocal call_count
            call_count += 1
            if event.get("event") == "on_custom_thinking":
                raise Exception("thinking callback error")
            # content callback succeeds

        sse = [
            'data: {"choices":[{"delta":{"reasoning_content":"t"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"a"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse)):
            content, thinking, _, _, _ = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk"},
                {"model": "m", "messages": []},
                stream_cb=_cb,
            )
        assert "".join(content) == "a"
        assert "".join(thinking) == "t"

    @pytest.mark.asyncio
    async def test_done_line_terminates_early(self):
        from streaming.llm_stream import stream_llm_response

        sse = [
            'data: {"choices":[{"delta":{"content":"only"},"finish_reason":null}]}',
            "data: [DONE]",
            'data: {"choices":[{"delta":{"content":"ignored"},"finish_reason":null}]}',
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse)):
            content, _, _, _, _ = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk"},
                {"model": "m", "messages": []},
            )
        assert "".join(content) == "only"

    @pytest.mark.asyncio
    async def test_no_stream_cb_no_error(self):
        from streaming.llm_stream import stream_llm_response

        sse = [
            'data: {"choices":[{"delta":{"content":"ok"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse)):
            content, _, _, _, _ = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk"},
                {"model": "m", "messages": []},
                stream_cb=None,
            )
        assert "".join(content) == "ok"

    @pytest.mark.asyncio
    async def test_empty_delta_content_skipped(self):
        from streaming.llm_stream import stream_llm_response

        sse = [
            'data: {"choices":[{"delta":{"content":""},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"real"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse)):
            content, _, _, _, _ = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk"},
                {"model": "m", "messages": []},
            )
        assert content == ["real"]
