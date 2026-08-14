"""Session CRUD publishes domain events to the user's cross-client channel."""

from unittest.mock import AsyncMock


def test_session_crud_publishes_events(client, monkeypatch):
    mock_publish = AsyncMock()
    monkeypatch.setattr("routers.sessions.publish_user_event", mock_publish)

    created = client.post("/api/sessions", json={"title": "evt-test"}).json()
    sid = created["id"]

    client.put(f"/api/sessions/{sid}", json={"title": "evt-renamed"})
    client.put(f"/api/sessions/{sid}/pin", json={"is_pinned": True})
    client.delete(f"/api/sessions/{sid}")

    types = [c.args[1]["type"] for c in mock_publish.await_args_list]
    assert "session.created" in types
    assert "session.updated" in types
    assert "session.deleted" in types

    deleted = [c for c in mock_publish.await_args_list if c.args[1]["type"] == "session.deleted"]
    assert deleted and deleted[0].args[1]["session_id"] == sid
