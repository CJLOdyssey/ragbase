import pytest
pytestmark = pytest.mark.integration

"""E2E Test: MCP CRUD operations."""

from tests.conftest import Api, _cleanup


class TestMCPCrud:
    def test_create_mcp(self, api: Api):
        r = api.post(
            "/api/mcps",
            json={
                "name": "E2E-MCP",
                "server_type": "stdio",
                "command": "python",
                "args": ["-m", "mcp_server"],
                "env": {"ROOT": "/data"},
                "is_active": True,
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["name"] == "E2E-MCP"
        _cleanup((body["id"], "/api/mcps"))

    def test_list_mcps(self, api: Api):
        r = api.get("/api/mcps")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_update_mcp(self, api: Api):
        r = api.post(
            "/api/mcps",
            json={
                "name": "Old",
                "server_type": "stdio",
                "command": "python",
                "args": [],
                "env": {},
            },
        )
        mid = r.json()["id"]
        r2 = api.put(f"/api/mcps/{mid}", json={"name": "New"})
        assert r2.status_code == 200
        assert r2.json()["name"] == "New"
        _cleanup((mid, "/api/mcps"))

    def test_delete_mcp(self, api: Api):
        r = api.post(
            "/api/mcps",
            json={
                "name": "Del",
                "server_type": "stdio",
                "command": "python",
                "args": [],
                "env": {},
            },
        )
        mid = r.json()["id"]
        r2 = api.delete(f"/api/mcps/{mid}")
        assert r2.status_code in (200, 204)
