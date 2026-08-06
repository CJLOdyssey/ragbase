"""Handler implementations for _ToolWrapper — dispatched from tool_config.py."""

from __future__ import annotations

import asyncio
import json
import shlex
import subprocess
import time
import urllib.request
from typing import TYPE_CHECKING, Any

import httpx
from core.infra.logging_config import get_logger
from langchain_core.messages import HumanMessage

if TYPE_CHECKING:
    from services.tool_config import _ToolWrapper

logger = get_logger(__name__)

def handle_skill(tool_self: _ToolWrapper, args: dict[str, Any]) -> str:
    """Return the skill's instruction text as the tool result.

    An unconfigured skill (no instructions) returns a clear message instead of
    an empty result, so the model doesn't misread it as "nothing to do".
    """
    if tool_self.instructions:
        return tool_self.instructions
    return json.dumps({
        "role": "skill",
        "name": tool_self.name,
        "status": "unconfigured",
        "content": (
            f"技能 {tool_self.name} 未配置使用说明（instructions 为空）。"
            "请在技能管理中填写 instructions 后再调用此技能。"
        ),
    }, ensure_ascii=False)


async def handle_mcp(tool_self: _ToolWrapper, args: dict[str, Any]) -> str:
    """Dispatch an MCP tool call."""
    return await execute_mcp(tool_self, args)


async def call_http_endpoint(tool_self: _ToolWrapper, args: dict[str, Any]) -> str:
    """Call an HTTP endpoint with the tool's configured method and headers.

    Endpoint may contain ``{param}`` placeholders (RFC 6570 URI template) —
    matching keys are taken from *args* and substituted into the path; any
    remaining args are sent as query params (GET) or JSON body (other methods).
    """
    try:
        hdrs = json.loads(tool_self.headers) if isinstance(tool_self.headers, str) else {}
        hdrs.setdefault("Content-Type", "application/json")

        url = tool_self.endpoint
        query_args: dict[str, Any] = dict(args)
        if "{" in url:
            path_args, query_args = {}, dict(args)
            for key, value in list(query_args.items()):
                token = "{" + str(key) + "}"
                if token in url:
                    url = url.replace(token, str(value))
                    path_args[key] = value
            query_args = {k: v for k, v in query_args.items() if k not in path_args}

        async with httpx.AsyncClient(timeout=30.0) as client:
            if tool_self.method.upper() == "GET":
                resp = await client.get(url, params=query_args, headers=hdrs)
            else:
                resp = await client.post(url, json=query_args, headers=hdrs)
            resp.raise_for_status()
            return resp.text
    except httpx.HTTPStatusError as e:
        return json.dumps({"tool": tool_self.name, "error": f"HTTP {e.response.status_code}: {e.response.text[:500]}"})
    except Exception as e:
        return json.dumps({"tool": tool_self.name, "error": str(e)})


async def execute_mcp(tool_self: _ToolWrapper, args: dict[str, Any]) -> str:
    """MCP execution: sse → httpx, stdio → mcp SDK, fallback → execute_tool."""
    if tool_self.mcp_type == "sse" and tool_self.mcp_endpoint:
        try:
            params = {"name": tool_self.mcp_tool_name or tool_self.name, "arguments": args}
            body = json.dumps({"jsonrpc": "2.0", "method": "tools/call", "params": params, "id": 1})
            async with httpx.AsyncClient(timeout=30) as client:
                hdrs = {"Content-Type": "application/json"}
                resp = await client.post(tool_self.mcp_endpoint, content=body, headers=hdrs)
                return resp.text[:5000]
        except Exception as e:
            return json.dumps({"error": str(e)})

    if tool_self.mcp_type == "stdio" and tool_self.mcp_endpoint:
        return await call_mcp_sdk(tool_self, args)

    result = execute_tool(tool_self, args)
    logger.debug("MCP fallback to tool execution | tool=%s", tool_self.name)
    return result


def execute_tool(tool_self: _ToolWrapper, args: dict[str, Any]) -> str:
    """Execute a tool: HTTP POST or local command."""
    if tool_self.mcp_endpoint:
        if tool_self.mcp_endpoint.startswith("http://") or tool_self.mcp_endpoint.startswith("https://"):
            try:
                body = json.dumps(args).encode()
                req = urllib.request.Request(
                    tool_self.mcp_endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST"
                )
                with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
                    data: bytes = resp.read()
                    return data.decode("utf-8", errors="ignore")[:5000]
            except Exception as e:
                return json.dumps({"error": str(e)})
        else:
            try:
                cmd = [tool_self.mcp_endpoint] + [str(v) for v in args.values()]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                stdout = result.stdout[:3000]
                stderr = result.stderr[:500]
                return json.dumps({"stdout": stdout, "stderr": stderr, "rc": result.returncode})
            except subprocess.TimeoutExpired:
                return json.dumps({"error": "timeout (30s)"})
            except Exception as e:
                return json.dumps({"error": str(e)})
    return json.dumps({"status": "called", "args": args})


def _normalize_mcp_env(env: Any) -> dict[str, str] | None:
    """Normalize MCP env config (dict or list of ``K=V`` strings) for ``StdioServerParameters``."""
    if not env:
        return None
    if isinstance(env, dict):
        return {str(k): str(v) for k, v in env.items()}
    if isinstance(env, (list, tuple)):
        out: dict[str, str] = {}
        for item in env:
            if isinstance(item, str) and "=" in item:
                key, _, value = item.partition("=")
                out[key.strip()] = value
        return out or None
    return None


def _mcp_params(tool_self: _ToolWrapper) -> Any:
    """Build ``StdioServerParameters`` from ``tool_self.mcp_config``.

    Falls back to ``shlex.split(tool_self.mcp_endpoint)`` for legacy tool
    definitions that inline args in the endpoint string.
    """
    from mcp import StdioServerParameters

    cfg = tool_self.mcp_config or {}
    if isinstance(cfg, str):
        try:
            cfg = json.loads(cfg)
        except Exception:
            cfg = {}
    if not isinstance(cfg, dict):
        cfg = {}
    cmd = cfg.get("command") or tool_self.mcp_endpoint
    args = cfg.get("args") or []
    env = _normalize_mcp_env(cfg.get("env"))
    if args:
        return StdioServerParameters(command=str(cmd), args=[str(a) for a in args], env=env)
    cmd_parts = shlex.split(cmd)
    return StdioServerParameters(command=cmd_parts[0], args=cmd_parts[1:], env=env)


async def call_mcp_sdk(tool_self: _ToolWrapper, args: dict[str, Any]) -> str:
    """Call MCP stdio tool, caching sessions per run_id so browser state persists."""
    from mcp.client.session import ClientSession
    from mcp.client.stdio import stdio_client

    async def _call(session: Any, name: str | None, arguments: dict[str, Any] | None, timeout: int = 45) -> Any:
        if name:
            return await asyncio.wait_for(session.call_tool(name, arguments=arguments or {}), timeout=timeout)
        return await asyncio.wait_for(session.list_tools(), timeout=20)

    # Discovery calls (no specific tool name) always create fresh connections
    if not tool_self.mcp_tool_name:
        params = _mcp_params(tool_self)
        try:
            async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
                await session.initialize()
                result = await _call(session, None, None)
        except Exception as e:
            return json.dumps({"error": str(e)})
        tools = getattr(result, "tools", [])
        if tools:
            lines = []
            for t in tools:
                props: dict[str, Any] = {}
                if hasattr(t, "inputSchema") and t.inputSchema:
                    props = t.inputSchema.get("properties", {}) or {}
                desc = "; ".join(f"{k}: {v.get('description','')}" for k, v in props.items()) if props else ""
                lines.append(f"- {t.name}: {t.description or ''} [{desc}]")
            return ("MCP server provides:\n" + "\n".join(lines) +
                    "\n\nTo call one, pass {\"_tool\": \"TOOL_NAME\", \"_args\": {...}}")
        return json.dumps({"error": "no tools found"})

    params = _mcp_params(tool_self)
    run_key = tool_self._run_id or ""

    # Create fresh session per call.  We deliberately do NOT cache the session
    # across calls: anyio's cancel scopes used by stdio_client/ClientSession are
    # task-scoped, and re-entering/exiting them from a different task raises
    # "Attempted to exit cancel scope in a different task".  A fresh `async with`
    # keeps enter/exit in the same task and is safe.
    try:
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            result = await _call(session, tool_self.mcp_tool_name, args)
            if tool_self.name and "browser_" in tool_self.name and tool_self._run_id:
                await _push_mcp_screenshot(session, tool_self._run_id)
            texts = _extract_mcp_texts(result)
            return texts if texts else json.dumps({"result": "ok"})
    except asyncio.CancelledError:
        # Do NOT let CancelledError escape to the graph: agent_pipeline wraps
        # graph.run in asyncio.timeout, whose cancel scope can collide with
        # anyio's internal scope when spawning the MCP stdio subprocess. Swallow
        # it and return an error string so the run can converge instead of crashing.
        logger.warning("MCP call cancelled (run=%s tool=%s) — suppressing", run_key[:12], tool_self.name)
        return json.dumps({"tool": tool_self.name, "error": "MCP 调用被中断（子进程启动超时或取消）"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _extract_mcp_texts(result: Any) -> str:
    """Extract text content from MCP tool result."""
    content_list = getattr(result, "content", [])
    texts = [getattr(c, "text", "") for c in content_list if getattr(c, "text", "")]
    texts = [t for t in texts if t]
    return "\n".join(texts) if texts else ""


async def _push_mcp_screenshot(session: Any, run_id: str | None) -> None:
    """Take a screenshot after browser tool call and push to frontend via WebSocket."""
    if not run_id:
        return
    try:
        r = await session.call_tool("browser_take_screenshot", {"type": "png"})
        for c in (r.content or []):
            if hasattr(c, "type") and c.type == "image" and hasattr(c, "data") and c.data:
                from broker import publish_run_message
                await publish_run_message(run_id, {"type": "browser_frame", "data": c.data})
                return
    except Exception:
        pass


async def llm_fallback(tool_self: _ToolWrapper, args: dict[str, Any]) -> str:
    """Use an LLM as a fallback executor when no other handler matches."""
    if tool_self._llm:
        try:
            prompt = (
                f"You are the '{tool_self.name}' tool. "
                f"Your description: {tool_self.description or 'No description'}.\n"
                "Execute this tool call and return ONLY the result "
                "as plain text or JSON (no markdown, no explanation):\n"
                f"Arguments: {json.dumps(args, ensure_ascii=False)}\n"
                "Output:"
            )
            t0 = time.time()
            resp = await tool_self._llm.ainvoke([HumanMessage(content=prompt)])
            elapsed = time.time() - t0
            logger.info(
                "LLM tool-fallback | tool=%s | model=%s | elapsed=%.2fs | out=%d chars",
                tool_self.name, getattr(tool_self._llm, 'model', '?'), elapsed, len(resp.content or ""),
            )
            return resp.content
        except Exception as e:
            return json.dumps({"tool": tool_self.name, "status": "error", "error": str(e)})
    note = "no LLM available, falling back"
    return json.dumps({"tool": tool_self.name, "status": "executed", "note": note, "args": args})
