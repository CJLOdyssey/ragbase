"""Targeted tests for observability/router.py uncovered branches."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_store():
    store = MagicMock()
    store.by_trace.return_value = [{"trace_id": "t1", "level": "INFO"}]
    store.search.return_value = [{"message": "found"}]
    store.recent_errors.return_value = [{"error_type": "TypeError"}]
    store.slow_events.return_value = [{"duration_ms": 5000}]
    store.stats.return_value = {"by_level": {"INFO": 1}, "errors": 0}
    store._query.return_value = [{"cnt": 1}]
    store.self_check.return_value = {
        "queue_size": 0, "write_errors": 0, "disk_errors": 0,
        "disk_free_mb": 100, "disk_min_free_mb": 100, "writer_alive": True,
        "closed": False, "last_heartbeat": 0, "db_path": ":memory:",
    }
    return store


class TestListEventsBranches:
    @patch("observability.router.get_store")
    def test_trace_id_filter(self, mock_get_store, mock_store, client):
        mock_get_store.return_value = mock_store
        resp = client.get("/api/debug/events?trace_id=t1")
        assert resp.status_code == 200
        mock_store.by_trace.assert_called_once()

    @patch("observability.router.get_store")
    def test_q_filter(self, mock_get_store, mock_store, client):
        mock_get_store.return_value = mock_store
        resp = client.get("/api/debug/events?q=search-term")
        assert resp.status_code == 200
        mock_store.search.assert_called_once()

    @patch("observability.router.get_store")
    def test_errors_filter(self, mock_get_store, mock_store, client):
        mock_get_store.return_value = mock_store
        resp = client.get("/api/debug/events?errors=true")
        assert resp.status_code == 200
        mock_store.recent_errors.assert_called_once()

    @patch("observability.router.get_store")
    def test_slow_filter(self, mock_get_store, mock_store, client):
        mock_get_store.return_value = mock_store
        resp = client.get("/api/debug/events?slow=2000")
        assert resp.status_code == 200
        mock_store.slow_events.assert_called_once()


class TestTraceDetail:
    @patch("observability.router.analyze_trace")
    def test_trace_detail(self, mock_analyze, client):
        mock_analyze.return_value = {"trace_id": "abc", "events": [], "suggestion": None}
        resp = client.get("/api/debug/trace/abc")
        assert resp.status_code == 200
        data = resp.json()
        assert data["trace_id"] == "abc"


class TestHealthException:
    @patch("observability.router.get_store")
    def test_health_returns_500_on_query_failure(self, mock_get_store, mock_store, client_strict):
        """Lines 83-84: exception inside the try block returns 500 JSONResponse."""
        store = MagicMock()
        store._query.side_effect = RuntimeError("query failed")
        mock_get_store.return_value = store
        resp = client_strict.get("/api/debug/health")
        assert resp.status_code == 500
        data = resp.json()
        assert data["status"] == "error"
        assert data["write_errors"] == -1

    @patch("observability.router.get_store")
    def test_health_returns_500_on_self_check_failure(self, mock_get_store, mock_store, client_strict):
        store = MagicMock()
        store._query.return_value = [{"cnt": 1}]
        store.self_check.side_effect = RuntimeError("self_check failed")
        mock_get_store.return_value = store
        resp = client_strict.get("/api/debug/health")
        assert resp.status_code == 500
        data = resp.json()
        assert data["status"] == "error"


class TestHealthDegraded:
    @patch("observability.router.get_store")
    @patch("observability.router.guard_health", return_value={"crashed": True})
    def test_health_degraded_when_crashed(self, mock_guard, mock_get_store, client):
        store = MagicMock()
        store._query.return_value = [{"cnt": 5}]
        store.self_check.return_value = {
            "queue_size": 0, "write_errors": 0, "disk_errors": 0,
            "disk_free_mb": 100, "disk_min_free_mb": 100, "writer_alive": True,
            "closed": False, "last_heartbeat": 0, "db_path": ":memory:",
        }
        mock_get_store.return_value = store
        resp = client.get("/api/debug/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"

    @patch("observability.router.get_store")
    @patch("observability.router.guard_health", return_value={"status": "ok"})
    def test_health_degraded_when_write_errors(self, mock_guard, mock_get_store, client):
        store = MagicMock()
        store._query.return_value = [{"cnt": 5}]
        store.self_check.return_value = {
            "queue_size": 0, "write_errors": 5, "disk_errors": 0,
            "disk_free_mb": 100, "disk_min_free_mb": 100, "writer_alive": True,
            "closed": False, "last_heartbeat": 0, "db_path": ":memory:",
        }
        mock_get_store.return_value = store
        resp = client.get("/api/debug/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"

    @patch("observability.router.get_store")
    @patch("observability.router.guard_health", return_value={"status": "ok"})
    def test_health_degraded_when_disk_errors(self, mock_guard, mock_get_store, client):
        store = MagicMock()
        store._query.return_value = [{"cnt": 5}]
        store.self_check.return_value = {
            "queue_size": 0, "write_errors": 0, "disk_errors": 3,
            "disk_free_mb": 100, "disk_min_free_mb": 100, "writer_alive": True,
            "closed": False, "last_heartbeat": 0, "db_path": ":memory:",
        }
        mock_get_store.return_value = store
        resp = client.get("/api/debug/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"

    @patch("observability.router.get_store")
    @patch("observability.router.guard_health", return_value={"status": "ok"})
    def test_health_degraded_when_large_queue(self, mock_guard, mock_get_store, client):
        store = MagicMock()
        store._query.return_value = [{"cnt": 5}]
        store.self_check.return_value = {
            "queue_size": 200, "write_errors": 0, "disk_errors": 0,
            "disk_free_mb": 100, "disk_min_free_mb": 100, "writer_alive": True,
            "closed": False, "last_heartbeat": 0, "db_path": ":memory:",
        }
        mock_get_store.return_value = store
        resp = client.get("/api/debug/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
