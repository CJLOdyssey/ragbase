import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.tool_config import _ToolWrapper
from services.tool_handlers import (
    call_http_endpoint,
    call_mcp_sdk,
    execute_mcp,
    execute_tool,
    handle_mcp,
    handle_skill,
    llm_fallback,
)


@pytest.fixture
def wrapper():
    return _ToolWrapper(
        name="test-tool",
        description="A test tool",
        instructions="Follow instructions",
    )


@pytest.fixture
def http_wrapper():
    return _ToolWrapper(
        name="http-tool",
        description="HTTP tool",
        endpoint="https://api.example.com/data",
        method="POST",
        headers='{"Authorization": "Bearer test"}',
    )


@pytest.fixture
def mcp_wrapper():
    return _ToolWrapper(
        name="mcp-tool",
        description="MCP tool",
        mcp_type="sse",
        mcp_endpoint="https://mcp.example.com/rpc",
        mcp_tool_name="get_info",
    )


class TestHandleSkill:
    def test_handle_skill_with_instructions(self, wrapper):
        result = handle_skill(wrapper, {"input": "hello"})
        assert result == "Follow instructions"

    def test_handle_skill_without_instructions(self):
        w = _ToolWrapper(name="bare-skill")
        result = handle_skill(w, {})
        parsed = json.loads(result)
        assert parsed["role"] == "skill"
        assert parsed["name"] == "bare-skill"
        assert parsed["status"] == "unconfigured"

    def test_skill_prefix_routes_unconfigured_to_handle_skill(self):
        from services.tool_config import _ToolWrapper as W

        W = W(name="skill_xlsx")
        result = handle_skill(W, {})
        parsed = json.loads(result)
        assert parsed["status"] == "unconfigured"
        assert "instructions" in parsed["content"]


class TestCallHttpEndpoint:
    @pytest.mark.asyncio
    async def test_get_request(self):
        w = _ToolWrapper(name="getter", endpoint="https://example.com/data", method="GET")
        mock_response = AsyncMock()
        mock_response.text = '{"key": "value"}'
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client
            mock_client.get.return_value = mock_response

            result = await call_http_endpoint(w, {"id": "42"})

            assert result == '{"key": "value"}'
            mock_client.get.assert_called_once_with(
                "https://example.com/data", params={"id": "42"}, headers={"Content-Type": "application/json"}
            )

    @pytest.mark.asyncio
    async def test_get_request_path_template(self):
        """{param} placeholders in the endpoint are substituted from args;
        remaining args go to the query string."""
        w = _ToolWrapper(name="weather", endpoint="https://wttr.in/{location}", method="GET")
        mock_response = AsyncMock()
        mock_response.text = "Beijing: +30C"
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client
            mock_client.get.return_value = mock_response

            result = await call_http_endpoint(w, {"location": "Beijing", "format": "3"})

            assert result == "Beijing: +30C"
            mock_client.get.assert_called_once_with(
                "https://wttr.in/Beijing", params={"format": "3"}, headers={"Content-Type": "application/json"}
            )

    @pytest.mark.asyncio
    async def test_post_request(self, http_wrapper):
        mock_response = AsyncMock()
        mock_response.text = '{"status": "ok"}'
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client
            mock_client.post.return_value = mock_response

            result = await call_http_endpoint(http_wrapper, {"name": "test"})

            assert result == '{"status": "ok"}'
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_http_error(self, http_wrapper):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client
            from httpx import HTTPStatusError, Request

            mock_client.post.side_effect = HTTPStatusError(
                "404", request=MagicMock(spec=Request), response=MagicMock(status_code=404, text="Not Found")
            )

            result = await call_http_endpoint(http_wrapper, {})
            parsed = json.loads(result)
            assert "error" in parsed
            assert "HTTP" in parsed["error"]


class TestHandleMcp:
    @pytest.mark.asyncio
    async def test_handle_mcp_sse(self, mcp_wrapper):
        mock_response = AsyncMock()
        mock_response.text = '{"result": "ok"}'

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client
            mock_client.post.return_value = mock_response

            result = await handle_mcp(mcp_wrapper, {"foo": "bar"})
            assert result == '{"result": "ok"}'

    @pytest.mark.asyncio
    async def test_handle_mcp_mocked(self):
        w = _ToolWrapper(name="mcp", mcp_type="mocked")
        with patch("services.tool_handlers.execute_tool", return_value="mock result"):
            result = await handle_mcp(w, {})
            assert result == "mock result"


class TestExecuteMcp:
    @pytest.mark.asyncio
    async def test_execute_mcp_sse(self, mcp_wrapper):
        mock_response = AsyncMock()
        mock_response.text = "mcp result"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client
            mock_client.post.return_value = mock_response

            result = await execute_mcp(mcp_wrapper, {"x": 1})
            assert result == "mcp result"

    @pytest.mark.asyncio
    async def test_execute_mcp_sse_error(self):
        w = _ToolWrapper(name="mcp", mcp_type="sse", mcp_endpoint="https://mcp.example.com/rpc")
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client
            mock_client.post.side_effect = Exception("Connection refused")

            result = await execute_mcp(w, {})
            parsed = json.loads(result)
            assert "error" in parsed

    @pytest.mark.asyncio
    async def test_execute_mcp_fallback_to_execute_tool(self):
        w = _ToolWrapper(name="fallback")
        with patch("services.tool_handlers.execute_tool", return_value='{"status": "called"}'):
            result = await execute_mcp(w, {})
            assert "called" in result


class TestExecuteTool:
    def test_execute_tool_http_endpoint(self):
        w = _ToolWrapper(name="tool", mcp_endpoint="https://api.example.com/run")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'{"done": true}'
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            result = execute_tool(w, {"input": "test"})
            assert "done" in result

    def test_execute_tool_local_command(self):
        w = _ToolWrapper(name="tool", mcp_endpoint="/usr/bin/echo")
        result = execute_tool(w, {"input": "hello"})
        assert "stdout" in result

    def test_execute_tool_no_endpoint(self):
        w = _ToolWrapper(name="bare")
        result = execute_tool(w, {})
        parsed = json.loads(result)
        assert parsed["status"] == "called"

    def test_execute_tool_command_timeout(self):
        w = _ToolWrapper(name="tool", mcp_endpoint="/usr/bin/sleep")
        # Mock subprocess.run to raise TimeoutExpired instantly — the real
        # path would run `/usr/bin/sleep 60` and block for 30s.
        import subprocess

        with patch("services.tool_handlers.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["sleep"], timeout=30)):
            result = execute_tool(w, {"input": "60"})
        parsed = json.loads(result)
        assert "error" in parsed
        assert "timeout" in parsed["error"]


class TestLlmFallback:
    @pytest.mark.asyncio
    async def test_llm_fallback_with_llm(self):
        w = _ToolWrapper(name="llm-tool", description="LLM-powered tool")
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "Generated result"
        mock_llm.ainvoke.return_value = mock_response
        w._llm = mock_llm

        result = await llm_fallback(w, {"query": "test"})
        assert result == "Generated result"

    @pytest.mark.asyncio
    async def test_llm_fallback_without_llm(self):
        w = _ToolWrapper(name="no-llm-tool")
        result = await llm_fallback(w, {"query": "test"})
        parsed = json.loads(result)
        assert parsed["status"] == "executed"

    @pytest.mark.asyncio
    async def test_llm_fallback_llm_error(self):
        w = _ToolWrapper(name="failing-llm")
        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = Exception("Rate limit exceeded")
        w._llm = mock_llm

        result = await llm_fallback(w, {"query": "test"})
        parsed = json.loads(result)
        assert parsed["status"] == "error"
        assert "Rate limit exceeded" in parsed["error"]


class TestCallHttpEndpointEdgeCases:
    @pytest.mark.asyncio
    async def test_generic_exception(self):
        w = _ToolWrapper(name="failing-http", endpoint="https://example.com/fail", method="POST")
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client
            mock_client.post.side_effect = Exception("Connection timeout")

            result = await call_http_endpoint(w, {})
            parsed = json.loads(result)
            assert "error" in parsed
            assert "Connection timeout" in parsed["error"]

    @pytest.mark.asyncio
    async def test_get_request_generic_error(self):
        w = _ToolWrapper(name="failing-get", endpoint="https://example.com/fail", method="GET")
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client
            mock_client.get.side_effect = Exception("DNS error")

            result = await call_http_endpoint(w, {})
            parsed = json.loads(result)
            assert "error" in parsed


class TestExecuteToolEdgeCases:
    def test_execute_tool_http_error(self):
        w = _ToolWrapper(name="tool", mcp_endpoint="https://api.example.com/run")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = Exception("Connection refused")
            result = execute_tool(w, {})
            parsed = json.loads(result)
            assert "error" in parsed

    def test_execute_tool_http_parse_error(self):
        w = _ToolWrapper(name="tool", mcp_endpoint="https://api.example.com/run")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = Exception("Parse error: unexpected token")
            result = execute_tool(w, {})
            parsed = json.loads(result)
            assert "error" in parsed

    def test_execute_tool_generic_exception(self):
        w = _ToolWrapper(name="tool", mcp_endpoint="/usr/bin/false")
        result = execute_tool(w, {})
        parsed = json.loads(result)
        assert "error" in parsed or "rc" in parsed

    def test_execute_tool_subprocess_raises(self):
        w = _ToolWrapper(name="tool", mcp_endpoint="nonexistent_cmd_xyz")
        result = execute_tool(w, {})
        parsed = json.loads(result)
        assert "error" in parsed


class TestCallMcpSdk:
    @pytest.mark.asyncio
    async def test_call_mcp_sdk_successful_call(self):
        w = _ToolWrapper(
            name="mcp-stdio",
            mcp_type="stdio",
            mcp_endpoint="/usr/bin/env",
            mcp_tool_name="test_cmd",
        )
        mock_result = MagicMock()
        mock_result.content = [MagicMock(text="tool output")]
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        with patch("mcp.client.stdio.stdio_client") as mock_stdio:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_stdio.return_value.__aenter__.return_value = (mock_read, mock_write)
            with patch("mcp.client.session.ClientSession", return_value=mock_session) as mock_cs:
                mock_cs.return_value.__aenter__.return_value = mock_session
                result = await call_mcp_sdk(w, {"x": 1})
                assert "tool output" in result

    @pytest.mark.asyncio
    async def test_call_mcp_sdk_list_tools(self):
        w = _ToolWrapper(
            name="mcp-stdio",
            mcp_type="stdio",
            mcp_endpoint="/usr/bin/env",
            mcp_tool_name="",
        )
        mock_result = MagicMock()
        mock_tool = MagicMock()
        mock_tool.name = "list_tool"
        mock_tool.description = "Lists things"
        mock_tool.inputSchema = {"properties": {"x": {"description": "the x"}}}
        mock_result.tools = [mock_tool]

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=mock_result)

        with patch("mcp.client.stdio.stdio_client") as mock_stdio:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_stdio.return_value.__aenter__.return_value = (mock_read, mock_write)
            with patch("mcp.client.session.ClientSession", return_value=mock_session) as mock_cs:
                mock_cs.return_value.__aenter__.return_value = mock_session
                result = await call_mcp_sdk(w, {})
                assert "MCP server provides" in result
                assert "list_tool" in result

    @pytest.mark.asyncio
    async def test_call_mcp_sdk_error_is_caught(self):
        w = _ToolWrapper(
            name="mcp-stdio",
            mcp_type="stdio",
            mcp_endpoint="/usr/bin/env",
            mcp_tool_name="test_cmd",
        )
        with patch("services.tool_handlers.call_mcp_sdk", new_callable=AsyncMock) as mock_sdk:
            mock_sdk.return_value = '{"error": "mcp not available"}'
            result = await execute_mcp(w, {})
            assert "error" in result

    @pytest.mark.asyncio
    async def test_call_mcp_sdk_result_no_content(self):
        w = _ToolWrapper(
            name="mcp-stdio",
            mcp_type="stdio",
            mcp_endpoint="/usr/bin/env",
            mcp_tool_name="empty_cmd",
        )
        mock_result = MagicMock()
        mock_result.content = []
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        with patch("mcp.client.stdio.stdio_client") as mock_stdio:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_stdio.return_value.__aenter__.return_value = (mock_read, mock_write)
            with patch("mcp.client.session.ClientSession", return_value=mock_session) as mock_cs:
                mock_cs.return_value.__aenter__.return_value = mock_session
                result = await call_mcp_sdk(w, {})
                assert "result" in result

    @pytest.mark.asyncio
    async def test_call_mcp_sdk_builds_params_from_mcp_config(self):
        """mcp_config args/env must reach StdioServerParameters; endpoint inline args ignored."""
        w = _ToolWrapper(
            name="mcp-stdio",
            mcp_type="stdio",
            mcp_endpoint="node legacy.js --old",
            mcp_tool_name="test_cmd",
            mcp_config={
                "command": "/usr/bin/env",
                "args": ["--foo", "bar"],
                "env": ["FOO=1", "BAR=two"],
            },
        )
        w._run_id = "run-mcp-cfg"
        mock_result = MagicMock()
        mock_result.content = [MagicMock(text="tool output")]
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        with patch("mcp.client.stdio.stdio_client") as mock_stdio:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_stdio.return_value.__aenter__.return_value = (mock_read, mock_write)
            with patch("mcp.client.session.ClientSession", return_value=mock_session) as mock_cs:
                mock_cs.return_value.__aenter__.return_value = mock_session
                result = await call_mcp_sdk(w, {"x": 1})

        assert "tool output" in result
        params = mock_stdio.call_args[0][0]
        assert params.command == "/usr/bin/env"
        assert params.args == ["--foo", "bar"]
        assert params.env == {"FOO": "1", "BAR": "two"}

    @pytest.mark.asyncio
    async def test_call_mcp_sdk_mcp_config_json_string(self):
        """mcp_config may be a JSON string (e.g. parsed from DB config column)."""
        w = _ToolWrapper(
            name="mcp-stdio",
            mcp_type="stdio",
            mcp_endpoint="node server.js",
            mcp_tool_name="test_cmd",
            mcp_config=json.dumps({
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                "env": {"X": "Y"},
            }),
        )
        w._run_id = "run-mcp-json"
        mock_result = MagicMock()
        mock_result.content = [MagicMock(text="ok")]
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        with patch("mcp.client.stdio.stdio_client") as mock_stdio:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_stdio.return_value.__aenter__.return_value = (mock_read, mock_write)
            with patch("mcp.client.session.ClientSession", return_value=mock_session) as mock_cs:
                mock_cs.return_value.__aenter__.return_value = mock_session
                await call_mcp_sdk(w, {})

        params = mock_stdio.call_args[0][0]
        assert params.command == "npx"
        assert params.args == ["-y", "@modelcontextprotocol/server-filesystem"]
        assert params.env == {"X": "Y"}

    @pytest.mark.asyncio
    async def test_call_mcp_sdk_legacy_shlex_fallback(self):
        """Without mcp_config, endpoint is shlex.split() as before."""
        w = _ToolWrapper(
            name="mcp-stdio",
            mcp_type="stdio",
            mcp_endpoint="node server.js --port 3000",
            mcp_tool_name="test_cmd",
        )
        w._run_id = "run-mcp-legacy"
        mock_result = MagicMock()
        mock_result.content = [MagicMock(text="ok")]
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        with patch("mcp.client.stdio.stdio_client") as mock_stdio:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_stdio.return_value.__aenter__.return_value = (mock_read, mock_write)
            with patch("mcp.client.session.ClientSession", return_value=mock_session) as mock_cs:
                mock_cs.return_value.__aenter__.return_value = mock_session
                await call_mcp_sdk(w, {})

        params = mock_stdio.call_args[0][0]
        assert params.command == "node"
        assert params.args == ["server.js", "--port", "3000"]
        assert params.env is None
