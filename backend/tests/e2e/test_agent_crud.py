import pytest

pytestmark = pytest.mark.integration

"""E2E Test: Agent CRUD operations + full config."""

from tests.conftest import Api, _cleanup, _rid


class TestAgentCRUD:
    """E2E tests for agent create, read, update, and delete operations."""

    def test_create_agent_full_config(self, api: Api):
        """Create an agent with all optional config fields populated."""
        r = api.post(
            "/api/agents",
            json={
                "name": "E2E-Agent",
                "role_identifier": _rid("e2e_agent"),
                "system_prompt": "你是E2E测试助手",
                "output_constraints": "请用中文回答",
                "model": "deepseek-v4-flash",
                "temperature": 0.7,
                "tools": [{"name": "custom_tool", "enabled": True}],
                "mcp": [{"name": "file_server", "config": {"root": "/tmp"}}],
                "skills": [{"name": "code_review", "version": "1.0"}],
                "is_active": True,
                "icon": "🤖",
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert "id" in body
        assert body["status"] == "created"
        aid = body["id"]
        r2 = api.get(f"/api/agents/{aid}")
        assert r2.status_code == 200
        a = r2.json()
        assert a["system_prompt"] == "你是E2E测试助手"
        assert a["output_constraints"] == "请用中文回答"
        assert a["model"] == "deepseek-v4-flash"
        assert a["temperature"] == 0.7
        assert isinstance(a["tools"], list)
        assert a["tools"][0]["name"] == "custom_tool"
        _cleanup((aid, "/api/agents"))

    def test_create_agent_minimal(self, api: Api):
        """Create an agent with only required fields."""
        r = api.post(
            "/api/agents",
            json={
                "name": "Minimal-Agent",
                "role_identifier": _rid("minimal"),
                "system_prompt": "Hello",
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert "id" in body
        _cleanup((body["id"], "/api/agents"))

    def test_update_agent(self, api: Api):
        """Update an agent's name and system prompt."""
        r = api.post(
            "/api/agents",
            json={
                "name": "Old-Name",
                "role_identifier": _rid("old"),
                "system_prompt": "old",
            },
        )
        aid = r.json()["id"]
        r2 = api.put(
            f"/api/agents/{aid}",
            json={
                "name": "New-Name",
                "system_prompt": "new prompt",
            },
        )
        assert r2.status_code == 200
        body = r2.json()
        assert body["status"] == "updated"
        r3 = api.get(f"/api/agents/{aid}")
        assert r3.json()["name"] == "New-Name"
        assert r3.json()["system_prompt"] == "new prompt"
        _cleanup((aid, "/api/agents"))

    def test_delete_agent(self, api: Api):
        """Delete an agent and verify status response."""
        r = api.post(
            "/api/agents",
            json={
                "name": "Del-Agent",
                "role_identifier": _rid("del"),
                "system_prompt": "x",
            },
        )
        assert r.status_code == 201, r.text
        aid = r.json()["id"]
        r2 = api.delete(f"/api/agents/{aid}")
        assert r2.status_code == 200
        assert r2.json()["status"] == "deleted"

    def test_toggle_agent(self, api: Api):
        """Toggle an agent's active state."""
        r = api.post(
            "/api/agents",
            json={
                "name": "Toggle-Agent",
                "role_identifier": _rid("toggle_agent"),
                "system_prompt": "x",
                "is_active": True,
            },
        )
        aid = r.json()["id"]
        r2 = api.put(f"/api/agents/{aid}/toggle")
        assert r2.status_code == 200
        body = r2.json()
        assert body.get("is_active") is False
        _cleanup((aid, "/api/agents"))

    def test_list_agents_full_fields(self, api: Api):
        """List agents and verify all expected fields are present."""
        r = api.get("/api/agents")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        if data:
            item = data[0]
            expected = {
                "id",
                "name",
                "role_identifier",
                "system_prompt",
                "output_constraints",
                "tools",
                "mcp",
                "skills",
                "model",
                "temperature",
                "order",
                "is_active",
                "is_approver",
                "icon",
                "created_at",
            }
            assert expected.issubset(item.keys()), f"Missing keys: {expected - item.keys()}"
