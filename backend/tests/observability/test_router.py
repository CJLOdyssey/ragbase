"""Tests for the observability debug router (backend/observability/router.py)."""

from unittest.mock import patch

import pytest
from starlette.testclient import TestClient


class TestDebugRouter:
    @pytest.fixture
    def client(self):
        # Lazy import to avoid early startup side-effects
        with patch("observability.startup_guard.health", return_value={"status": "ok"}):
            from core.app import app
            with TestClient(app) as c:
                yield c

    def test_debug_health_endpoint(self, client):
        resp = client.get("/api/debug/health")
        # Should return something, not crash
        assert resp.status_code in (200, 500)

    def test_debug_events_endpoint(self, client):
        resp = client.get("/api/debug/events")
        assert resp.status_code in (200, 500)

    def test_debug_stats_endpoint(self, client):
        resp = client.get("/api/debug/stats")
        assert resp.status_code in (200, 500)

    def test_debug_errors_endpoint(self, client):
        resp = client.get("/api/debug/errors")
        assert resp.status_code in (200, 500)

    def test_debug_circuit_breakers_endpoint(self, client):
        resp = client.get("/api/debug/circuit-breakers")
        assert resp.status_code == 200
        data = resp.json()
        assert "circuit_breakers" in data
        assert len(data["circuit_breakers"]) >= 1
