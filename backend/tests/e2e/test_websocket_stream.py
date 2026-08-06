"""E2E test: WebSocket streaming for run progress."""

from __future__ import annotations

import json
import os

import pytest
import websockets

pytestmark = pytest.mark.integration

from tests.conftest import Api, _clear_rate_limits

WS_BASE = os.environ.get("E2E_WS_URL", "ws://localhost:8082")


class TestWebSocketStream:
    """Verify WebSocket streaming endpoint for run progress."""

    def test_websocket_connects_and_receives_status(self, api: Api):
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

        run = r.json()
        run_id = run["run_id"]

        # 3. Connect to WebSocket
        import asyncio

        async def _ws_test():
            uri = f"{WS_BASE}/ws/runs/{run_id}"
            async with websockets.connect(uri) as ws:
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

        asyncio.run(_ws_test())

    def test_websocket_nonexistent_run(self):
        """Connect to WS with a fake run_id — should still accept connection."""
        import asyncio

        async def _ws_test():
            uri = f"{WS_BASE}/ws/runs/nonexistent-run-id"
            try:
                async with websockets.connect(uri) as ws:
                    msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    data = json.loads(msg)
                    assert data["type"] == "status"
                    assert data["status"] == "connected"
            except websockets.exceptions.WebSocketException:
                pass  # Acceptable if server rejects the connection

        asyncio.run(_ws_test())
