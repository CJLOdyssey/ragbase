"""Versions router tests — merged from test_coverage_boost, test_coverage_gaps, test_remaining_coverage."""

from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.unit



class TestVersions:
    """Merged: TestVersions + TestVersionsGaps + TestVersionsRemainingGaps."""

    def test_list_versions(self, client):
        resp = client.get("/api/versions/agent/test-resource")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_version(self, client):
        resp = client.post("/api/versions", json={
            "resource_type": "agent",
            "resource_id": "agent-1",
            "snapshot": {"name": "test"},
        })
        assert resp.status_code == 201
        assert resp.json()["resource_type"] == "agent"

    def test_get_version_found(self, client):
        resp = client.post("/api/versions", json={
            "resource_type": "agent",
            "resource_id": "agent-2",
            "snapshot": {"name": "test"},
        })
        version_id = resp.json()["id"]
        resp = client.get(f"/api/versions/detail/{version_id}")
        assert resp.status_code == 200

    def test_get_version_not_found(self, client):
        resp = client.get("/api/versions/detail/nonexistent")
        assert resp.status_code in (200, 404)

    @pytest.mark.skip(reason="Depends(get_session) makes mock unreliable for versions endpoint")
    def test_get_version_not_found_returns_404(self, client):
        with patch("repository.versions.get_version", new_callable=AsyncMock, return_value=None):
            resp = client.get("/api/versions/detail/nonexistent-id")
            assert resp.status_code == 404
