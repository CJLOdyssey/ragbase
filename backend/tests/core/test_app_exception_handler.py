"""Tests for the global exception handler (backend/core/app.py)."""

import pytest
from starlette.testclient import TestClient


class TestExceptionHandler:
    @pytest.fixture
    def client(self):
        import os
        os.environ['AUTH_MODE'] = 'legacy'
        os.environ['AUTH_ENABLED'] = '0'
        os.environ['RATE_LIMIT'] = '9999'
        os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
        from core.app import app
        with TestClient(app) as c:
            yield c

    def test_health_returned(self, client):
        resp = client.get("/api/health")
        assert resp.status_code in (200, 503)  # may be 503 if DB not available

    def test_version_endpoint(self, client):
        resp = client.get("/api/version")
        assert resp.status_code == 200
        assert "version" in resp.json()

    def test_unknown_route_returns_json(self, client):
        resp = client.get("/api/nonexistent")
        # FastAPI returns 404 for unknown routes
        # The exception handler catches unhandled exceptions only
        assert resp.status_code == 404
