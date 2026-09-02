from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage


class TestConvertMessagesToApi:
    def test_system_message(self):
        from streaming.llm_stream import convert_messages_to_api

        msgs = [SystemMessage(content="You are a helpful assistant.")]
        result = convert_messages_to_api(msgs)
        assert result == [{"role": "system", "content": "You are a helpful assistant."}]

    def test_human_message(self):
        from streaming.llm_stream import convert_messages_to_api

        msgs = [HumanMessage(content="Hello!")]
        result = convert_messages_to_api(msgs)
        assert result == [{"role": "user", "content": "Hello!"}]

    def test_ai_message(self):
        from streaming.llm_stream import convert_messages_to_api

        msgs = [AIMessage(content="Hi there!")]
        result = convert_messages_to_api(msgs)
        assert result == [{"role": "assistant", "content": "Hi there!"}]

    def test_ai_message_with_tool_calls(self):
        from streaming.llm_stream import convert_messages_to_api

        msgs = [
            AIMessage(
                content="I will search.",
                tool_calls=[
                    {"id": "call_1", "name": "search", "args": {"query": "test"}},
                ],
            )
        ]
        result = convert_messages_to_api(msgs)
        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        assert result[0]["tool_calls"][0]["id"] == "call_1"
        assert result[0]["tool_calls"][0]["function"]["name"] == "search"

    def test_tool_message(self):
        from streaming.llm_stream import convert_messages_to_api

        msgs = [ToolMessage(content='{"result": "ok"}', tool_call_id="call_1")]
        result = convert_messages_to_api(msgs)
        assert result == [
            {"role": "tool", "tool_call_id": "call_1", "content": '{"result": "ok"}'}
        ]

    def test_mixed_messages(self):
        from streaming.llm_stream import convert_messages_to_api

        msgs = [
            SystemMessage(content="Be helpful."),
            HumanMessage(content="Hi"),
            AIMessage(content="Hello!"),
            ToolMessage(content="done", tool_call_id="c1"),
        ]
        result = convert_messages_to_api(msgs)
        assert len(result) == 4
        assert [m["role"] for m in result] == ["system", "user", "assistant", "tool"]

    def test_empty_list(self):
        from streaming.llm_stream import convert_messages_to_api

        assert convert_messages_to_api([]) == []


class TestBuildLlmRequestBody:
    def test_minimal_body(self):
        from streaming.llm_stream import build_llm_request_body

        url, headers, body = build_llm_request_body(
            [{"role": "user", "content": "hello"}],
            model="deepseek-chat",
            api_key="sk-test",
        )
        assert "api.deepseek.com" in url
        assert url.endswith("/chat/completions")
        assert headers["Authorization"] == "Bearer sk-test"
        assert body["model"] == "deepseek-chat"
        assert body["stream"] is True
        assert body["thinking"] == {"type": "enabled"}

    def test_custom_base_url(self):
        from streaming.llm_stream import build_llm_request_body

        url, headers, body = build_llm_request_body(
            [{"role": "user", "content": "hi"}],
            model="gpt-4",
            api_key="sk-xxx",
            base_url="https://api.openai.com/v1",
        )
        assert url == "https://api.openai.com/v1/chat/completions"
        assert "thinking" not in body

    def test_with_tool_definitions(self):
        from streaming.llm_stream import build_llm_request_body

        tools = [{
            "type": "function",
            "function": {"name": "get_weather", "description": "Get weather"},
        }]
        url, headers, body = build_llm_request_body(
            [{"role": "user", "content": "weather?"}],
            model="deepseek-chat",
            api_key="sk-test",
            tool_definitions=tools,
        )
        assert body["tools"] == tools
        assert body["tool_choice"] == "auto"
        assert "thinking" not in body

    def test_custom_temperature_max_tokens(self):
        from streaming.llm_stream import build_llm_request_body

        url, headers, body = build_llm_request_body(
            [{"role": "user", "content": "hi"}],
            model="deepseek-chat",
            api_key="sk-test",
            temperature=0.1,
            max_tokens=1024,
        )
        assert body["temperature"] == 0.1
        assert body["max_tokens"] == 1024

    def test_default_max_tokens_within_common_provider_limit(self):
        # 65536 exceeds SiliconFlow Qwen models' max_seq_len (32768) → 400.
        # The default must fit mainstream providers (DeepSeek/Qwen/Groq/OpenRouter).
        from streaming.llm_stream import build_llm_request_body

        url, headers, body = build_llm_request_body(
            [{"role": "user", "content": "hi"}],
            model="Qwen/Qwen3-8B",
            api_key="sk-test",
        )
        assert body["max_tokens"] <= 16384


class TestBuildToolCallsList:
    def test_consolidates_fragments(self):
        from streaming.llm_stream import build_tool_calls_list

        tool_calls_map = {
            0: {"id": "call_1", "name": "get_wea", "arguments": '{"loc": "NYC"}'},
            1: {"id": "call_2", "name": "search_", "arguments": '{"q": "test"}'},
        }
        result = build_tool_calls_list(tool_calls_map)
        assert len(result) == 2
        assert result[0]["id"] == "call_1"
        assert result[0]["name"] == "get_wea"
        assert result[0]["args"] == {"loc": "NYC"}

    def test_empty_map(self):
        from streaming.llm_stream import build_tool_calls_list

        assert build_tool_calls_list({}) == []

    def test_invalid_json_arguments(self):
        from streaming.llm_stream import build_tool_calls_list

        tool_calls_map = {
            0: {"id": "c1", "name": "test", "arguments": "not valid json {"},
        }
        result = build_tool_calls_list(tool_calls_map)
        assert result[0]["args"] == {}

    def test_empty_name_skipped(self):
        from streaming.llm_stream import build_tool_calls_list

        tool_calls_map = {
            0: {"id": "c1", "name": "", "arguments": "{}"},
        }
        result = build_tool_calls_list(tool_calls_map)
        assert result == []

    def test_sorted_by_index(self):
        from streaming.llm_stream import build_tool_calls_list

        tool_calls_map = {
            2: {"id": "c3", "name": "third", "arguments": '{"z": 1}'},
            0: {"id": "c1", "name": "first", "arguments": '{"a": 1}'},
            1: {"id": "c2", "name": "second", "arguments": '{"b": 1}'},
        }
        result = build_tool_calls_list(tool_calls_map)
        assert [r["id"] for r in result] == ["c1", "c2", "c3"]


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
            raise httpx.HTTPStatusError("error", request=MagicMock(), response=MagicMock())


class _MockClientCtx:
    def __init__(self, sse_lines, status_code=200):
        self._sse_lines = sse_lines
        self._status_code = status_code

    def stream(self, method, url, headers=None, json=None):
        return _MockStreamCtx(self._sse_lines, self._status_code)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return None


class TestStreamLlmResponse:
    @pytest.mark.asyncio
    async def test_streams_content_chunks(self):
        from streaming.llm_stream import stream_llm_response

        sse_lines = [
            'data: {"choices":[{"delta":{"content":"Hello"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":" world"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":""},"finish_reason":"stop","usage":{"input_tokens":10,"output_tokens":5}}]}',
            "data: [DONE]",
        ]

        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse_lines)):
            content, thinking, tool_calls, finish_reason, usage = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk-test"},
                {"model": "deepseek-chat", "messages": []},
            )
        assert "".join(content) == "Hello world"
        assert thinking == []
        assert tool_calls == {}
        assert finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_streams_reasoning_content(self):
        from streaming.llm_stream import stream_llm_response

        sse_lines = [
            'data: {"choices":[{"delta":{"reasoning_content":"Let me think"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"Answer"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]

        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse_lines)):
            content, thinking, tool_calls, finish_reason, usage = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk-test"},
                {"model": "deepseek-chat", "messages": []},
            )
        assert "".join(thinking) == "Let me think"
        assert "".join(content) == "Answer"
        assert finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_reasoning_content_sliced_think_tags_stripped(self):
        """GLM-Z1 reasoning_content wraps <think> sliced across token chunks."""
        from streaming.llm_stream import stream_llm_response

        sse_lines = [
            'data: {"choices":[{"delta":{"reasoning_content":"\\n<th"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"reasoning_content":"ink>\\n推理过程"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"reasoning_content":"</think>"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"正式回答"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]

        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse_lines)):
            content, thinking, tool_calls, finish_reason, usage = await stream_llm_response(
                "https://api.siliconflow.cn/v1/chat/completions",
                {"Authorization": "Bearer sk-test"},
                {"model": "THUDM/GLM-Z1-9B-0414", "messages": []},
            )
        assert "".join(thinking) == "推理过程"
        assert "".join(content) == "正式回答"

    @pytest.mark.asyncio
    async def test_strips_think_wrappers_from_reasoning_content(self):
        """SiliconFlow wraps GLM-Z1 reasoning_content in <think>; strip it."""
        from streaming.llm_stream import stream_llm_response

        sse_lines = [
            'data: {"choices":[{"delta":{"reasoning_content":"<think>推理过程</think>"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"正式回答"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]

        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse_lines)):
            content, thinking, tool_calls, finish_reason, usage = await stream_llm_response(
                "https://api.siliconflow.cn/v1/chat/completions",
                {"Authorization": "Bearer sk-test"},
                {"model": "THUDM/GLM-Z1-9B-0414", "messages": []},
            )
        assert "".join(thinking) == "推理过程"
        assert "".join(content) == "正式回答"

    @pytest.mark.asyncio
    async def test_splits_think_tags_from_content(self):
        """GLM-Z1-style models emit <think> inline in content; split into thinking."""
        from streaming.llm_stream import stream_llm_response

        sse_lines = [
            'data: {"choices":[{"delta":{"content":"<think>用户问"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"首都，需要回答北京。"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"</think>中国的首都是北京。"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]

        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse_lines)):
            content, thinking, tool_calls, finish_reason, usage = await stream_llm_response(
                "https://api.siliconflow.cn/v1/chat/completions",
                {"Authorization": "Bearer sk-test"},
                {"model": "THUDM/GLM-Z1-9B-0414", "messages": []},
            )
        assert "".join(thinking) == "用户问首都，需要回答北京。"
        assert "".join(content) == "中国的首都是北京。"
        assert finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_think_without_reasoning_content_ordering(self):
        """think-tag content is routed to the thinking stream, never to content."""
        from streaming.llm_stream import stream_llm_response

        sse_lines = [
            'data: {"choices":[{"delta":{"content":"<think>推理过程</think>正式回答"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]

        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse_lines)):
            content, thinking, tool_calls, finish_reason, usage = await stream_llm_response(
                "https://api.siliconflow.cn/v1/chat/completions",
                {"Authorization": "Bearer sk-test"},
                {"model": "THUDM/GLM-Z1-9B-0414", "messages": []},
            )
        assert "".join(thinking) == "推理过程"
        assert "".join(content) == "正式回答"

    @pytest.mark.asyncio
    async def test_parses_tool_call_deltas(self):
        from streaming.llm_stream import stream_llm_response

        sse_lines = [
            'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_1","function":{"name":"get_weather","arguments":""}}]},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"{\\"loc"}}]},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"ation\\": \\"NYC\\"}"}}]},"finish_reason":"tool_calls"}]}',
            "data: [DONE]",
        ]

        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse_lines)):
            content, thinking, tool_calls, finish_reason, usage = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk-test"},
                {"model": "deepseek-chat", "messages": []},
            )
        assert 0 in tool_calls
        assert tool_calls[0]["id"] == "call_1"
        assert tool_calls[0]["name"] == "get_weather"
        assert finish_reason == "tool_calls"

    @pytest.mark.asyncio
    async def test_skips_non_data_lines(self):
        from streaming.llm_stream import stream_llm_response

        sse_lines = [
            ":comment line",
            "event: custom",
            'data: {"choices":[{"delta":{"content":"hi"},"finish_reason":null}]}',
            "data: [DONE]",
        ]

        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse_lines)):
            content, thinking, tool_calls, finish_reason, usage = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk-test"},
                {"model": "deepseek-chat", "messages": []},
            )
        assert "".join(content) == "hi"

    @pytest.mark.asyncio
    async def test_handles_json_decode_error(self):
        from streaming.llm_stream import stream_llm_response

        sse_lines = [
            "data: {invalid json",
            'data: {"choices":[{"delta":{"content":"ok"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]

        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse_lines)):
            content, thinking, tool_calls, finish_reason, usage = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk-test"},
                {"model": "deepseek-chat", "messages": []},
            )
        assert "".join(content) == "ok"

    @pytest.mark.asyncio
    async def test_calls_stream_callback(self):
        from streaming.llm_stream import stream_llm_response

        callback = AsyncMock()
        sse_lines = [
            'data: {"choices":[{"delta":{"content":"A"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"B"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]

        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse_lines)):
            await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk-test"},
                {"model": "deepseek-chat", "messages": []},
                stream_cb=callback,
            )
        assert callback.await_count == 2

    @pytest.mark.asyncio
    async def test_raises_on_http_error(self):
        from streaming.llm_stream import stream_llm_response

        sse_lines = ["data: [DONE]"]

        with (
            patch("httpx.AsyncClient", return_value=_MockClientCtx(sse_lines, status_code=401)),
            pytest.raises(httpx.HTTPStatusError),
        ):
            await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk-test"},
                {"model": "deepseek-chat", "messages": []},
            )

    @pytest.mark.asyncio
    async def test_skips_chunk_with_no_choices(self):
        from streaming.llm_stream import stream_llm_response

        sse_lines = [
            'data: {"choices":[],"finish_reason":null}',
            'data: {"choices":[{"delta":{"content":"hi"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse_lines)):
            content, thinking, tool_calls, finish_reason, usage = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk-test"},
                {"model": "deepseek-chat", "messages": []},
            )
        assert "".join(content) == "hi"

    @pytest.mark.asyncio
    async def test_tagless_reasoning_streams_realtime_before_content(self):
        """DeepSeek reasoning_content carries no <think>: after the bounded
        tag wait it must stream real-time (thinking event before content)."""
        from streaming.llm_stream import stream_llm_response

        callback = AsyncMock()
        sse_lines = [
            'data: {"choices":[{"delta":{"reasoning_content":"这是一段超过十六个字符的深度思考过程文本"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"reasoning_content":"继续思考更多"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"Answer"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse_lines)):
            content, thinking, tool_calls, finish_reason, usage = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk-test"},
                {"model": "deepseek-chat", "messages": []},
                stream_cb=callback,
            )
        assert "".join(thinking) == "这是一段超过十六个字符的深度思考过程文本继续思考更多"
        assert "".join(content) == "Answer"
        # 实时性：thinking 事件先于 content 事件发出（未被 hold 到流结束）
        events = [c.args[0]["event"] for c in callback.call_args_list]
        assert events.index("on_custom_thinking") < events.index("on_custom_token")

    @pytest.mark.asyncio
    async def test_calls_callback_for_reasoning_content(self):
        from streaming.llm_stream import stream_llm_response

        callback = AsyncMock()
        sse_lines = [
            'data: {"choices":[{"delta":{"reasoning_content":"Let me think..."},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"Answer"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse_lines)):
            await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk-test"},
                {"model": "deepseek-chat", "messages": []},
                stream_cb=callback,
            )
        callback.assert_any_call({"event": "on_custom_thinking", "data": {"content": "Let me think..."}})

    @pytest.mark.asyncio
    async def test_pending_content_flushed_after_stream(self):
        from streaming.llm_stream import stream_llm_response

        sse_lines = [
            'data: {"choices":[{"delta":{"content":"Hello"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":" world"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse_lines)):
            content, thinking, tool_calls, finish_reason, usage = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk-test"},
                {"model": "deepseek-chat", "messages": []},
                tool_definitions=[{"type": "function", "function": {"name": "test"}}],
            )
        assert "".join(content) == "Hello world"

    @pytest.mark.asyncio
    async def test_pending_content_with_callback(self):
        from streaming.llm_stream import stream_llm_response

        callback = AsyncMock()
        sse_lines = [
            'data: {"choices":[{"delta":{"content":"pending"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":" content"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse_lines)):
            content, thinking, tool_calls, finish_reason, usage = await stream_llm_response(
                "https://api.deepseek.com/chat/completions",
                {"Authorization": "Bearer sk-test"},
                {"model": "deepseek-chat", "messages": []},
                stream_cb=callback,
                tool_definitions=[{"type": "function", "function": {"name": "test"}}],
            )
        assert "".join(content) == "pending content"
        callback.assert_any_call({"event": "on_custom_token", "data": {"content": "pending"}})
        callback.assert_any_call({"event": "on_custom_token", "data": {"content": " content"}})

    @pytest.mark.asyncio
    async def test_stream_line_guard_truncates(self):
        """行数守卫：超限截断视为完成，防止失控输出无限挂起 worker。"""
        from streaming.llm_stream import stream_llm_response

        sse_lines = [
            f'data: {{"choices":[{{"delta":{{"content":"t{i}"}},"finish_reason":null}}]}}'
            for i in range(10)
        ]
        with (
            patch("streaming.llm_stream._MAX_STREAM_LINES", 5),
            patch("httpx.AsyncClient", return_value=_MockClientCtx(sse_lines)),
        ):
            content, thinking, tool_calls, finish_reason, usage = await stream_llm_response(
                "https://api.siliconflow.cn/v1/chat/completions",
                {"Authorization": "Bearer sk-test"},
                {"model": "THUDM/GLM-Z1-9B-0414", "messages": []},
            )
        # 10 行内容仅前 5 行被消费（第 6 行触发 guard break）。
        assert "".join(content) == "t0t1t2t3t4"

    @pytest.mark.asyncio
    async def test_unclosed_think_tag_flushed_on_finish(self):
        """尾部未闭合 think 标签：finish() 刷新为 thinking（防丢失推理链）。"""
        from streaming.llm_stream import stream_llm_response

        # 与 splitters.ThinkTagSplitter 的标签保持一致（\x3c 转义避免
        # 编辑器/渲染层对尖括号标签的歧义）。
        think_open = "\x3cthink\x3e"
        callback = AsyncMock()
        sse_lines = [
            'data: {"choices":[{"delta":{"content":"' + think_open + '未闭合推理"}, "finish_reason":"stop"}]}',
            "data: [DONE]",
        ]
        with patch("httpx.AsyncClient", return_value=_MockClientCtx(sse_lines)):
            content, thinking, tool_calls, finish_reason, usage = await stream_llm_response(
                "https://api.siliconflow.cn/v1/chat/completions",
                {"Authorization": "Bearer sk-test"},
                {"model": "THUDM/GLM-Z1-9B-0414", "messages": []},
                stream_cb=callback,
            )
        assert "".join(thinking) == "未闭合推理"
        assert "".join(content) == ""
        callback.assert_any_call(
            {"event": "on_custom_thinking", "data": {"content": "未闭合推理"}}
        )
