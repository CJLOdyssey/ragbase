import pytest
pytestmark = pytest.mark.integration

"""E2E Test: Team CRUD operations."""

from tests.conftest import Api, _cleanup


class TestTeamCRUD:
    def test_create_team(self, api: Api):
        r = api.post("/api/teams", json={"name": "E2E-Team-Create"})
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["name"] == "E2E-Team-Create"
        assert "id" in body
        _cleanup((body["id"], "/api/teams"))

    def test_list_teams(self, api: Api):
        r = api.get("/api/teams")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        if data:
            item = data[0]
            assert all(k in item for k in ("id", "name", "order", "agents", "created_at"))

    def test_update_team(self, api: Api):
        r = api.post("/api/teams", json={"name": "E2E-Team-Old"})
        tid = r.json()["id"]
        r2 = api.put(f"/api/teams/{tid}", json={"name": "E2E-Team-New"})
        assert r2.status_code == 200
        assert r2.json()["name"] == "E2E-Team-New"
        _cleanup((tid, "/api/teams"))

    def test_delete_team(self, api: Api):
        r = api.post("/api/teams", json={"name": "E2E-Team-Del"})
        tid = r.json()["id"]
        r2 = api.delete(f"/api/teams/{tid}")
        assert r2.status_code in (200, 204)
