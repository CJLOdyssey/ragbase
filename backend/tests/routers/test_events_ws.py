"""Tests for the per-user event WebSocket channel (/api/ws/events)."""

import pytest
import starlette.websockets as ws_errors


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
