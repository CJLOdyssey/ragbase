"""Tests for the per-user event WebSocket channel (/api/ws/events)."""

from unittest.mock import MagicMock

import pytest
import starlette.websockets as ws_errors
from routers.events import _ws_user_id


async def _event_stream(*args: object, **kwargs: object):
    yield {"type": "session.deleted", "session_id": "s1", "ts": 1}


def test_user_events_ws_rejects_anonymous(client, monkeypatch):
    monkeypatch.setattr("routers.events._ws_user_id", lambda websocket: "")
    with client.websocket_connect("/api/ws/events") as websocket:
        assert websocket.receive_json() == {"type": "status", "status": "error", "error": "未登录"}
        with pytest.raises(ws_errors.WebSocketDisconnect) as exc_info:
            websocket.receive_json()
    assert exc_info.value.code == 1008


def test_user_events_ws_streams_user_events(client, monkeypatch):
    monkeypatch.setattr("routers.events._ws_user_id", lambda websocket: "u1")
    monkeypatch.setattr("routers.events.subscribe_user_events", _event_stream)
    with client.websocket_connect("/api/ws/events") as websocket:
        assert websocket.receive_json() == {"type": "status", "status": "connected"}
        assert websocket.receive_json() == {
            "type": "session.deleted",
            "session_id": "s1",
            "ts": 1,
        }


def test_user_events_ws_pings_on_idle(client, monkeypatch):
    """主循环 30s 空闲 → 发 ping 保活（半开连接检测）。"""
    import asyncio

    monkeypatch.setattr("routers.events._ws_user_id", lambda websocket: "u1")
    real_wait_for = asyncio.wait_for
    calls = {"n": 0}

    async def _first_timeout(coro, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError
        return await real_wait_for(coro, timeout=5)

    monkeypatch.setattr("routers.events.asyncio.wait_for", _first_timeout)
    with client.websocket_connect("/api/ws/events") as websocket:
        assert websocket.receive_json() == {"type": "status", "status": "connected"}
        assert websocket.receive_json() == {"type": "ping"}


class TestWsUserId:
    """_ws_user_id 身份解析各分支（cookie JWT，无 legacy 开关）。"""

    def test_empty_without_token(self):
        ws = MagicMock()
        ws.cookies.get.return_value = None
        assert _ws_user_id(ws) == ""

    def test_user_from_valid_token(self):
        import os

        from auth.auth_jwt import create_token

        token = create_token("u-1", os.environ["AUTH_SECRET"])
        ws = MagicMock()
        ws.cookies.get.return_value = token
        assert _ws_user_id(ws) == "u-1"

    def test_empty_when_invalid_token(self):
        ws = MagicMock()
        ws.cookies.get.return_value = "not-a-jwt"
        assert _ws_user_id(ws) == ""
