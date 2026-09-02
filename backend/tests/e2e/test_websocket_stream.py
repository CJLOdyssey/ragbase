"""E2E test: WebSocket streaming for run progress."""

from __future__ import annotations

import asyncio
import json
import os

import pytest
import websockets

pytestmark = pytest.mark.integration

from tests.conftest import Api, _clear_rate_limits, _obtain_token

WS_BASE = os.environ.get("E2E_WS_URL", "ws://localhost:8081")


def _ws_uri(run_id: str) -> str:
    """Build the run WS URI with the access token.

    ``/ws/*`` 由 AuthMiddleware 豁免，前端走 httpOnly cookie；httpx 连接时
    需显式携带 token（query param），与 events WS 的 cookie 校验保持同一来源。
    """
    token = _obtain_token()
    if token:
        return f"{WS_BASE}/ws/runs/{run_id}?token={token}"
    return f"{WS_BASE}/ws/runs/{run_id}"


async def _first_status(uri: str) -> dict:
    """Connect and return the first status message (or None if closed early)."""
    try:
        async with websockets.connect(uri) as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            return json.loads(msg)
    except (websockets.exceptions.WebSocketException, TimeoutError):
        return {}


class TestWebSocketStream:
    """Verify WebSocket streaming endpoint for run progress."""

    async def test_websocket_connects_and_receives_status(self, api: Api):
        """Connect to WS, create a run, verify connection status."""
        _clear_rate_limits()

        # 1. Create a session
        r = api.post("/api/sessions", json={"title": "WS-Test"})
        assert r.status_code == 201, r.text
        session = r.json()
        sid = session["id"]

        # 2. Create a run
        r = api.post(
            "/api/runs",
            json={
                "requirement": "test",
                "session_id": sid,
            },
        )
        # Run may succeed (LLM configured) or fail (no LLM) — either is valid
        assert r.status_code in (200, 400, 422, 500), r.text
        if r.status_code != 200:
            return  # Cannot test WS without a valid run_id

        run_id = r.json()["run_id"]

        # 3. Connect to WebSocket
        async with websockets.connect(_ws_uri(run_id)) as ws:
            # Should receive a status message first
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(msg)
            assert data["type"] == "status"
            assert data["status"] == "connected"

            # May receive more messages (streaming) or connection may close
            try:
                while True:
                    msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    data = json.loads(msg)
                    assert data["type"] in (
                        "status", "message", "result",
                        "thinking_stream", "thinking_done", "stream",
                    ), f"Unexpected message type: {data['type']}"
                    if data["type"] == "result":
                        break  # Run completed
            except (TimeoutError, websockets.ConnectionClosed):
                pass

    async def test_websocket_rejects_unauthenticated(self):
        """WS 无 token → 拒绝连接（认证前置），不再泄漏任意 run 流。"""
        data = await _first_status(f"{WS_BASE}/ws/runs/nonexistent-run-id")
        assert data.get("type") == "status", f"expected status message, got {data!r}"
        assert data.get("status") == "error"

    async def test_websocket_rejects_foreign_run(self, api: Api):
        """匿名连接已存在的真实 run → 必须拒绝（BOLA 防护），不泄露对话流。"""
        _clear_rate_limits()

        # 用当前用户建一个会话 + run（存在即好，不存在也能测拒绝路径）
        r = api.post("/api/sessions", json={"title": "WS-Foreign"})
        if r.status_code != 201:
            return
        sid = r.json()["id"]
        r = api.post("/api/runs", json={"requirement": "test", "session_id": sid})
        if r.status_code != 200:
            return
        run_id = r.json()["run_id"]

        # 无 token 的匿名连接访问真实存在的 run → 必须被拒绝
        data = await _first_status(f"{WS_BASE}/ws/runs/{run_id}")
        assert data.get("type") == "status", f"expected status message, got {data!r}"
        assert data.get("status") == "error"
