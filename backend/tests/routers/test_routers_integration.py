"""Integration tests for FastAPI REST API routes using in-memory SQLite and TestClient."""
import os
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.integration
from starlette.testclient import TestClient

os.environ['AUTH_MODE'] = 'legacy'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///:memory:'
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
os.environ['KEY_VAULT_SECRET'] = '0123456789abcdef0123456789abcdef'
os.environ['AUTH_ENABLED'] = '0'
os.environ['RATE_LIMIT'] = '9999'
os.environ['CHECKPOINTER_BACKEND'] = 'memory'
os.environ['DATABASE_POOL_SIZE'] = '0'

import core.infra.database as db_mod
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

if db_mod._async_engine is None:
    _sqlite_engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    db_mod._async_engine = _sqlite_engine
if db_mod._async_session_factory is None:
    db_mod._async_session_factory = async_sessionmaker(
        db_mod._async_engine if db_mod._async_engine is not None else create_async_engine('sqlite+aiosqlite:///:memory:'),
        expire_on_commit=False,
    )
db_mod.DATABASE_URL = 'sqlite+aiosqlite:///:memory:'

from core.app import app
from core.base import Base


@pytest.fixture
def client():
    import core.app_lifespan as lifespan_mod

    async def _safe_init_db():
        engine = db_mod.get_async_engine()
        async with engine.begin() as conn:
            # Self-contained reset: don't rely on the routers _reset_db
            # autouse fixture (not reliably ordered under xdist worksteal).
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        from core.seed import seed_default_roles_and_admin
        await seed_default_roles_and_admin()

    lifespan_mod.init_db = _safe_init_db

    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1
    mock_redis.expire.return_value = True
    mock_redis.ping.return_value = True
    mock_redis.publish.return_value = 1

    with patch('backend.broker.get_redis', return_value=mock_redis):
        with patch('backend.core.app_lifespan.get_redis', return_value=mock_redis):
            with TestClient(app) as c:
                yield c


class TestApiEndpoints:

    def test_health_check(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "degraded")
        assert "checks" in data
        assert "database" in data["checks"]

    def test_version_endpoint(self, client):
        resp = client.get("/api/version")
        assert resp.status_code == 200
        assert "version" in resp.json()

    def test_metrics_endpoint(self, client):
        resp = client.get("/api/metrics")
        assert resp.status_code == 200

    def test_models_list(self, client):
        resp = client.get("/api/models")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_admin_stats(self, client):
        resp = client.get("/api/admin/stats")
        assert resp.status_code == 200
        data = resp.json()
        for key in ("agents", "prompts", "tools", "mcps", "skills", "teams", "logs_today"):
            assert key in data

    def test_agents_list_empty(self, client):
        resp = client.get("/api/agents")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_and_list_agents(self, client):
        payload = {
            "name": "test-agent",
            "role_identifier": "test_role",
            "system_prompt": "You are a test agent",
        }
        resp = client.post("/api/agents", json=payload)
        assert resp.status_code == 201
        created = resp.json()
        assert "id" in created
        assert created.get("status") == "created"

        resp = client.get("/api/agents")
        assert resp.status_code == 200
        ids = [a["id"] for a in resp.json()]
        assert created["id"] in ids

    def test_tools_list(self, client):
        resp = client.get("/api/tools")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_tools_validate(self, client):
        payload = {"code": "def hello():\n    return 'world'", "language": "python"}
        resp = client.post("/api/tools/validate", json=payload)
        assert resp.status_code == 200
        assert "is_valid" in resp.json()

    def test_skills_list(self, client):
        resp = client.get("/api/skills")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_mcps_list(self, client):
        resp = client.get("/api/mcps")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_teams_list(self, client):
        resp = client.get("/api/teams")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_prompts_list(self, client):
        resp = client.get("/api/prompts")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_providers_list(self, client):
        resp = client.get("/api/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert "openai" in data

    def test_versions_list(self, client):
        resp = client.get("/api/versions/agent/test-nonexistent")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_keys_list(self, client):
        resp = client.get("/api/keys")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_commands_list(self, client):
        resp = client.get("/api/commands")
        assert resp.status_code == 200
        cmds = resp.json()
        assert isinstance(cmds, list)
        assert len(cmds) > 0

    def test_workflows_list(self, client):
        resp = client.get("/api/workflows")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_admin_logs(self, client):
        resp = client.get("/api/admin/logs")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data.get("items"), list)
        assert "total" in data

    def test_admin_activity(self, client):
        resp = client.get("/api/admin/activity")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_tool_plugins_list(self, client):
        resp = client.get("/api/tools/plugins")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestAgentCRUD:

    USER_HEADERS = {"X-User-ID": "admin"}

    def _create_agent(self, client, name="crud-agent", role="crud_role", prompt="You are a CRUD test agent"):
        payload = {"name": name, "role_identifier": role, "system_prompt": prompt}
        resp = client.post("/api/agents", json=payload, headers=self.USER_HEADERS)
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_agent_create_and_get_by_id(self, client):
        agent_id = self._create_agent(client)
        resp = client.get(f"/api/agents/{agent_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "crud-agent"
        assert data["role_identifier"] == "crud_role"

    def test_agent_update(self, client):
        agent_id = self._create_agent(client, "update-agent", "update_role")
        resp = client.put(f"/api/agents/{agent_id}", json={
            "name": "updated-agent",
            "system_prompt": "Updated prompt",
        }, headers=self.USER_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "updated"

        resp = client.get(f"/api/agents/{agent_id}")
        assert resp.json()["name"] == "updated-agent"
        assert resp.json()["system_prompt"] == "Updated prompt"

    def test_agent_delete(self, client):
        agent_id = self._create_agent(client, "delete-agent", "delete_role", "Delete me")
        resp = client.delete(f"/api/agents/{agent_id}", headers=self.USER_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        resp = client.get(f"/api/agents/{agent_id}")
        assert resp.status_code == 404

    def test_agent_duplicate_role_returns_409(self, client):
        payload = {"name": "dup-agent", "role_identifier": "dup_role", "system_prompt": "dup"}
        resp = client.post("/api/agents", json=payload, headers=self.USER_HEADERS)
        assert resp.status_code == 201

        resp = client.post("/api/agents", json=payload, headers=self.USER_HEADERS)
        assert resp.status_code == 409

    def test_agent_get_nonexistent_returns_404(self, client):
        resp = client.get("/api/agents/nonexistent-id-99999")
        assert resp.status_code == 404

    def test_agent_update_nonexistent_returns_404(self, client):
        resp = client.put("/api/agents/nonexistent-id-99999", json={"name": "nope"}, headers=self.USER_HEADERS)
        assert resp.status_code == 404

    def test_agent_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/api/agents/nonexistent-id-99999", headers=self.USER_HEADERS)
        assert resp.status_code == 404

    def test_agent_create_empty_body_returns_422(self, client):
        resp = client.post("/api/agents", json={}, headers=self.USER_HEADERS)
        assert resp.status_code == 422

    def test_agent_toggle(self, client):
        agent_id = self._create_agent(client, "toggle-agent", "toggle_role")
        resp = client.put(f"/api/agents/{agent_id}/toggle", headers=self.USER_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_active"] is False

        resp = client.put(f"/api/agents/{agent_id}/toggle", headers=self.USER_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True


class TestToolCRUD:

    def _create_tool(self, client, name="test-tool", category="api"):
        payload = {"name": name, "category": category, "description": "A test tool"}
        resp = client.post("/api/tools", json=payload)
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_tool_create(self, client):
        payload = {"name": "test-tool", "category": "api", "description": "A test tool"}
        resp = client.post("/api/tools", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["name"] == "test-tool"

    def test_tool_update(self, client):
        tool_id = self._create_tool(client, "tool-to-update", "api")
        resp = client.put(f"/api/tools/{tool_id}", json={
            "name": "updated-tool",
            "description": "Updated description",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "updated-tool"

    def test_tool_delete(self, client):
        tool_id = self._create_tool(client, "tool-to-delete", "api")
        resp = client.delete(f"/api/tools/{tool_id}")
        assert resp.status_code == 204

    def test_tool_get_nonexistent_returns_404(self, client):
        resp = client.put("/api/tools/nonexistent-id-99999", json={"name": "nope"})
        assert resp.status_code == 404

    def test_tool_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/api/tools/nonexistent-id-99999")
        assert resp.status_code == 404

    def test_tool_create_empty_body_returns_422(self, client):
        resp = client.post("/api/tools", json={})
        assert resp.status_code == 422


class TestTeamCRUD:

    def _create_team(self, client, name="test-team"):
        resp = client.post("/api/teams", json={"name": name, "description": "A test team"})
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_team_create_and_get(self, client):
        payload = {"name": "test-team", "description": "A test team"}
        resp = client.post("/api/teams", json=payload)
        assert resp.status_code == 201
        team_id = resp.json()["id"]

        resp = client.get(f"/api/teams/{team_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "test-team"
        assert data.get("description") == "A test team"

    def test_team_update(self, client):
        team_id = self._create_team(client, "team-to-update")
        resp = client.put(f"/api/teams/{team_id}", json={"name": "updated-team", "description": "Updated"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "updated-team"
        assert data["description"] == "Updated"

    def test_team_delete(self, client):
        team_id = self._create_team(client, "team-to-delete")
        resp = client.delete(f"/api/teams/{team_id}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_team_get_nonexistent_returns_404(self, client):
        resp = client.get("/api/teams/nonexistent-id-99999")
        assert resp.status_code == 404

    def test_team_update_nonexistent_returns_404(self, client):
        resp = client.put("/api/teams/nonexistent-id-99999", json={"name": "nope"})
        assert resp.status_code == 404

    def test_team_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/api/teams/nonexistent-id-99999")
        assert resp.status_code == 404

    def test_team_create_empty_body_returns_422(self, client):
        resp = client.post("/api/teams", json={})
        assert resp.status_code == 422


class TestMCPCRUD:

    def _create_mcp(self, client, name="test-mcp"):
        payload = {"name": name, "type": "stdio", "endpoint": "/usr/bin/env"}
        resp = client.post("/api/mcps", json=payload)
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_mcp_create(self, client):
        payload = {"name": "test-mcp", "type": "stdio", "endpoint": "/usr/bin/env"}
        resp = client.post("/api/mcps", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["name"] == "test-mcp"

    def test_mcp_list(self, client):
        self._create_mcp(client, "mcp-for-list")
        resp = client.get("/api/mcps")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_mcp_update(self, client):
        mcp_id = self._create_mcp(client, "mcp-to-update")
        resp = client.put(f"/api/mcps/{mcp_id}", json={"name": "updated-mcp"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "updated-mcp"

    def test_mcp_delete(self, client):
        mcp_id = self._create_mcp(client, "mcp-to-delete")
        resp = client.delete(f"/api/mcps/{mcp_id}")
        assert resp.status_code == 204

    def test_mcp_get_nonexistent_returns_404(self, client):
        resp = client.put("/api/mcps/nonexistent-id-99999", json={"name": "nope"})
        assert resp.status_code == 404

    def test_mcp_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/api/mcps/nonexistent-id-99999")
        assert resp.status_code == 404

    def test_mcp_create_empty_body_returns_422(self, client):
        resp = client.post("/api/mcps", json={})
        assert resp.status_code == 422


class TestSkillCRUD:

    def _create_skill(self, client, name="test-skill", category="general"):
        payload = {"name": name, "category": category, "description": "A test skill"}
        resp = client.post("/api/skills", json=payload)
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_skill_create(self, client):
        payload = {"name": "test-skill", "category": "general", "description": "A test skill"}
        resp = client.post("/api/skills", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["name"] == "test-skill"

    def test_skill_update(self, client):
        skill_id = self._create_skill(client, "skill-to-update")
        resp = client.put(f"/api/skills/{skill_id}", json={"name": "updated-skill", "description": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "updated-skill"

    def test_skill_delete(self, client):
        skill_id = self._create_skill(client, "skill-to-delete")
        resp = client.delete(f"/api/skills/{skill_id}")
        assert resp.status_code == 204

    def test_skill_get_nonexistent_returns_404(self, client):
        resp = client.get("/api/skills/nonexistent-id-99999")
        assert resp.status_code == 404

    def test_skill_update_nonexistent_returns_404(self, client):
        resp = client.put("/api/skills/nonexistent-id-99999", json={"name": "nope"})
        assert resp.status_code == 404

    def test_skill_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/api/skills/nonexistent-id-99999")
        assert resp.status_code == 404

    def test_skill_create_empty_body_returns_422(self, client):
        resp = client.post("/api/skills", json={})
        assert resp.status_code == 422


class TestPromptCRUD:

    def _create_prompt(self, client, name="test-prompt", category="general"):
        payload = {"name": name, "category": category, "content": "You are a helpful assistant."}
        resp = client.post("/api/prompts", json=payload)
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_prompt_create(self, client):
        payload = {"name": "test-prompt", "category": "general", "content": "You are a helpful assistant."}
        resp = client.post("/api/prompts", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["name"] == "test-prompt"

    def test_prompt_update(self, client):
        prompt_id = self._create_prompt(client, "prompt-to-update")
        resp = client.put(f"/api/prompts/{prompt_id}", json={"name": "updated-prompt", "content": "Updated content"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "updated-prompt"
        assert data["content"] == "Updated content"

    def test_prompt_delete(self, client):
        prompt_id = self._create_prompt(client, "prompt-to-delete")
        resp = client.delete(f"/api/prompts/{prompt_id}")
        assert resp.status_code == 204

    def test_prompt_get_nonexistent_returns_404(self, client):
        resp = client.put("/api/prompts/nonexistent-id-99999", json={"name": "nope"})
        assert resp.status_code == 404

    def test_prompt_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/api/prompts/nonexistent-id-99999")
        assert resp.status_code == 404

    def test_prompt_create_empty_body_returns_422(self, client):
        resp = client.post("/api/prompts", json={})
        assert resp.status_code == 422


class TestSessionCRUD:

    USER_HEADERS = {"X-User-ID": "admin"}

    def _create_session(self, client, title="test-session"):
        resp = client.post("/api/sessions", json={"title": title}, headers=self.USER_HEADERS)
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_session_create_and_list(self, client):
        resp = client.post("/api/sessions", json={"title": "test-session"}, headers=self.USER_HEADERS)
        assert resp.status_code == 201
        session_id = resp.json()["id"]
        assert resp.json()["title"] == "test-session"

        resp = client.get("/api/sessions", headers=self.USER_HEADERS)
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()]
        assert session_id in ids

    def test_session_detail(self, client):
        session_id = self._create_session(client, "detail-session")
        resp = client.get(f"/api/sessions/{session_id}", headers=self.USER_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "detail-session"
        assert "runs" in data
        assert "memories" in data

    def test_session_rename(self, client):
        session_id = self._create_session(client, "rename-me")
        resp = client.put(f"/api/sessions/{session_id}", json={"title": "renamed-session"}, headers=self.USER_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["title"] == "renamed-session"

    def test_session_delete(self, client):
        session_id = self._create_session(client, "delete-me")
        resp = client.delete(f"/api/sessions/{session_id}", headers=self.USER_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    def test_session_get_nonexistent_returns_404(self, client):
        resp = client.get("/api/sessions/nonexistent-id-99999", headers=self.USER_HEADERS)
        assert resp.status_code == 404

    def test_session_update_nonexistent_returns_404(self, client):
        resp = client.put("/api/sessions/nonexistent-id-99999", json={"title": "nope"}, headers=self.USER_HEADERS)
        assert resp.status_code == 404

    def test_session_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/api/sessions/nonexistent-id-99999", headers=self.USER_HEADERS)
        assert resp.status_code == 404

    def test_session_rename_empty_body_returns_422(self, client):
        resp = client.put("/api/sessions/nonexistent-id", json={}, headers=self.USER_HEADERS)
        assert resp.status_code == 422


class TestKeyCRUD:

    USER_HEADERS = {"X-User-ID": "admin"}

    def test_key_create(self, client):
        payload = {
            "provider": "openai",
            "capabilities": ["embedding"],
            "label": "test-key",
            "api_key": "sk-test-key-value",
        }
        resp = client.post("/api/keys", json=payload, headers=self.USER_HEADERS)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["provider"] == "openai"

    def test_key_list(self, client):
        resp = client.get("/api/keys", headers=self.USER_HEADERS)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_key_create_empty_body_returns_422(self, client):
        resp = client.post("/api/keys", json={}, headers=self.USER_HEADERS)
        assert resp.status_code == 422


class TestWorkflowCRUD:

    def _create_workflow_team(self, client, suffix="wf"):
        resp = client.post("/api/teams", json={"name": f"wf-team-{suffix}"})
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_workflow_create(self, client):
        team_id = self._create_workflow_team(client, "create")
        payload = {
            "teamId": team_id,
            "name": "test-workflow",
            "maxRounds": 5,
            "nodes": [],
            "edges": [],
        }
        resp = client.post("/api/workflows", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "test-workflow"

    def test_workflow_list(self, client):
        team_id = self._create_workflow_team(client, "list")
        payload = {
            "teamId": team_id,
            "name": "list-wf",
            "maxRounds": 3,
            "nodes": [],
            "edges": [],
        }
        client.post("/api/workflows", json=payload)
        resp = client.get("/api/workflows")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_workflow_delete(self, client):
        team_id = self._create_workflow_team(client, "del")
        payload = {
            "teamId": team_id,
            "name": "del-wf",
            "maxRounds": 3,
            "nodes": [],
            "edges": [],
        }
        resp = client.post("/api/workflows", json=payload)
        wf_id = resp.json()["id"]
        resp = client.delete(f"/api/workflows/{wf_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"


class TestRunBasic:

    def test_create_run(self, client):
        import routers.runs as runs_router

        mock_result = {
            "run_id": "test-run-id-123",
            "session_id": "test-session-id-456",
            "status": "running",
        }
        with patch.object(runs_router.run_service, 'create_run', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_result
            resp = client.post("/api/runs", json={"requirement": "test requirement"}, headers={"X-User-ID": "admin"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["run_id"] == "test-run-id-123"
            assert data["status"] == "running"
            assert data["session_id"] == "test-session-id-456"

    def test_list_runs(self, client):
        import routers.runs as runs_router

        with patch.object(runs_router.run_service, 'list_runs', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [
                {"id": "run-1", "requirement": "test 1", "status": "converged"},
                {"id": "run-2", "requirement": "test 2", "status": "running"},
            ]
            resp = client.get("/api/runs")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0]["id"] == "run-1"


class TestDebugEndpoints:

    def test_debug_health(self, client):
        resp = client.get("/api/debug/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "events_stored" in data
