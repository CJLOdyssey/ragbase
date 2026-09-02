"""Versions router tests — merged from test_coverage_boost, test_coverage_gaps, test_remaining_coverage."""

import pytest

pytestmark = pytest.mark.unit



class TestVersions:
    """Merged: TestVersions + TestVersionsGaps + TestVersionsRemainingGaps."""

    def test_list_versions(self, client):
        resp = client.get("/api/versions/prompt/test-resource")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_versions_unknown_resource_type_rejected(self, client):
        # QA A5-04: unregistered resource types are rejected up front
        # instead of being queried blindly.
        resp = client.get("/api/versions/agent/test-resource")
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"]["code"] == "GENERAL_002"

    def test_create_version(self, client):
        resp = client.post("/api/versions", json={
            "resource_type": "prompt",
            "resource_id": "prompt-1",
            "snapshot": {"name": "test"},
        })
        assert resp.status_code == 201
        assert resp.json()["resource_type"] == "prompt"

    def test_create_version_unknown_resource_type_rejected(self, client):
        resp = client.post("/api/versions", json={
            "resource_type": "agent",
            "resource_id": "agent-1",
            "snapshot": {"name": "test"},
        })
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"]["code"] == "GENERAL_002"

    def test_get_version_found(self, client):
        resp = client.post("/api/versions", json={
            "resource_type": "prompt",
            "resource_id": "prompt-2",
            "snapshot": {"name": "test"},
        })
        version_id = resp.json()["id"]
        resp = client.get(f"/api/versions/detail/{version_id}")
        assert resp.status_code == 200

    def test_get_version_not_found(self, client):
        # /detail must match the detail route, not be swallowed by the
        # parametric /{resource_type}/{resource_id} route.
        resp = client.get("/api/versions/detail/nonexistent")
        assert resp.status_code == 404
