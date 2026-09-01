"""Tests for the observability debug router (backend/observability/router.py)."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_store():
    """Fake EventStore whose query methods return deterministic payloads."""
    store = MagicMock()
    store.recent.return_value = [{"trace_id": "t1", "level": "INFO"}]
    store.stats.return_value = {"by_level": {"INFO": 1}, "errors": 0}
    store.recent_errors.return_value = []
    store.count.return_value = 0
    store.self_check.return_value = {
        "queue_size": 0,
        "write_errors": 0,
        "disk_errors": 0,
        "disk_free_mb": 100,
        "disk_min_free_mb": 100,
        "writer_alive": True,
        "closed": False,
        "last_heartbeat": 0,
        "db_path": ":memory:",
    }
    return store


class TestDebugRouter:
    @patch("observability.router.get_store")
    def test_debug_health_endpoint(self, mock_get_store, mock_store, client):
        mock_get_store.return_value = mock_store
        resp = client.get("/api/debug/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["events_stored"] == 0
        assert "startup" in data
        assert "write_errors" in data

    @patch("observability.router.get_store")
    def test_debug_events_endpoint(self, mock_get_store, mock_store, client):
        mock_get_store.return_value = mock_store
        resp = client.get("/api/debug/events")
        assert resp.status_code == 200
        data = resp.json()
        assert data["events"] == [{"trace_id": "t1", "level": "INFO"}]
        assert data["total"] == 1

    @patch("observability.router.get_store")
    def test_debug_stats_endpoint(self, mock_get_store, mock_store, client):
        mock_get_store.return_value = mock_store
        resp = client.get("/api/debug/stats")
        assert resp.status_code == 200
        assert resp.json()["by_level"] == {"INFO": 1}

    @patch("observability.router.get_store")
    def test_debug_errors_endpoint(self, mock_get_store, mock_store, client):
        mock_get_store.return_value = mock_store
        resp = client.get("/api/debug/errors")
        assert resp.status_code == 200
        assert resp.json() == {"reports": []}

    def test_debug_circuit_breakers_endpoint(self, client):
        resp = client.get("/api/debug/circuit-breakers")
        assert resp.status_code == 200
        data = resp.json()
        assert "circuit_breakers" in data
        assert len(data["circuit_breakers"]) >= 1
