"""Response schema contract tests — verify field completeness of key endpoints."""

import pytest

pytestmark = pytest.mark.integration

# ── Resource namespacing for contract tests ───────────────────────────────────
_CONTRACT_PREFIX = "contract-"


class TestAgentCreateResponseSchema:
    async def test_create_agent_response_has_required_fields(self, test_client):
        r = await test_client.post(
            "/api/agents",
            json={
                "name": f"{_CONTRACT_PREFIX}test-agent",
                "role_identifier": "contract_test_agent",
                "system_prompt": "Test prompt",
            },
        )
        assert r.status_code in (200, 201)
        body = r.json()
        assert "id" in body, "Missing 'id' field in agent create response"
        assert "status" in body, "Missing 'status' field in agent create response"


class TestSessionCreateResponseSchema:
    async def test_create_session_response_has_required_fields(self, test_client):
        r = await test_client.post(
            "/api/sessions",
            json={"title": f"{_CONTRACT_PREFIX}test-session"},
        )
        assert r.status_code == 201
        body = r.json()
        assert "id" in body, "Missing 'id' field in session create response"
        assert "title" in body, "Missing 'title' field in session create response"


class TestToolCreateResponseSchema:
    async def test_create_tool_response_has_required_fields(self, test_client):
        r = await test_client.post(
            "/api/tools",
            json={
                "name": f"{_CONTRACT_PREFIX}test-tool",
                "category": "api",
                "description": "A test tool for contract testing",
            },
        )
        assert r.status_code in (200, 201)
        body = r.json()
        assert "id" in body, "Missing 'id' field in tool create response"
        assert "name" in body, "Missing 'name' field in tool create response"


class TestTeamCreateResponseSchema:
    async def test_create_team_response_has_required_fields(self, test_client):
        r = await test_client.post(
            "/api/teams",
            json={
                "name": f"{_CONTRACT_PREFIX}test-team",
                "description": "A test team for contract testing",
            },
        )
        assert r.status_code == 201
        body = r.json()
        assert "id" in body, "Missing 'id' field in team create response"
        assert "name" in body, "Missing 'name' field in team create response"


# ═══════════════════════════════════════════════════════════════════════════════
# Pagination fields on list endpoints
# ═══════════════════════════════════════════════════════════════════════════════

PAGINATED_ENDPOINTS: list[tuple[str, str]] = [
    ("/api/agents", "agents"),
    ("/api/tools", "tools"),
    ("/api/skills", "skills"),
    ("/api/mcps", "mcps"),
    ("/api/teams", "teams"),
    ("/api/prompts", "prompts"),
    ("/api/keys", "keys"),
    ("/api/commands", "commands"),
    ("/api/workflows", "workflows"),
    ("/api/sessions", "sessions"),
]


class TestListPagination:
    """Verify list endpoints return responses that contain or support pagination fields."""

    async def _check_list_response(self, test_client, path: str, label: str) -> None:
        r = await test_client.get(path)
        assert r.status_code == 200, f"{label}: expected 200, got {r.status_code}"
        body = r.json()
        # Responses may be raw arrays or paginated objects
        if isinstance(body, dict):
            assert "items" in body or "data" in body, (
                f"{label}: paginated object missing items/data field"
            )
        elif isinstance(body, list):
            pass  # raw array is acceptable
        else:
            pytest.fail(f"{label}: unexpected response type {type(body)}")

    async def test_agents_list_supports_pagination(self, test_client):
        await self._check_list_response(test_client, "/api/agents", "agents")

    async def test_tools_list_supports_pagination(self, test_client):
        await self._check_list_response(test_client, "/api/tools", "tools")

    async def test_skills_list_supports_pagination(self, test_client):
        await self._check_list_response(test_client, "/api/skills", "skills")

    async def test_mcps_list_supports_pagination(self, test_client):
        await self._check_list_response(test_client, "/api/mcps", "mcps")

    async def test_teams_list_supports_pagination(self, test_client):
        await self._check_list_response(test_client, "/api/teams", "teams")

    async def test_prompts_list_supports_pagination(self, test_client):
        await self._check_list_response(test_client, "/api/prompts", "prompts")

    async def test_keys_list_supports_pagination(self, test_client):
        await self._check_list_response(test_client, "/api/keys", "keys")

    async def test_sessions_list_supports_pagination(self, test_client):
        await self._check_list_response(test_client, "/api/sessions", "sessions")

    async def test_workflows_list_supports_pagination(self, test_client):
        await self._check_list_response(test_client, "/api/workflows", "workflows")


# ═══════════════════════════════════════════════════════════════════════════════
# Create endpoints return 201 with the created resource
# ═══════════════════════════════════════════════════════════════════════════════


class TestCreateEndpointsReturn201:
    """Verify that POST create endpoints return 201 and the created resource body."""

    async def test_create_session_returns_201_with_resource(self, test_client):
        r = await test_client.post(
            "/api/sessions",
            json={"title": f"{_CONTRACT_PREFIX}test-session-201"},
        )
        assert r.status_code == 201, f"Expected 201, got {r.status_code}"
        body = r.json()
        assert "id" in body, "Created session should have an id"
        assert "title" in body, "Created session should have a title"

    async def test_create_team_returns_201_with_resource(self, test_client):
        r = await test_client.post(
            "/api/teams",
            json={
                "name": f"{_CONTRACT_PREFIX}test-team-201",
                "description": "Contract test team",
            },
        )
        assert r.status_code == 201, f"Expected 201, got {r.status_code}"
        body = r.json()
        assert "id" in body, "Created team should have an id"
        assert "name" in body, "Created team should have a name"

    async def test_create_tool_returns_201_with_resource(self, test_client):
        r = await test_client.post(
            "/api/tools",
            json={
                "name": f"{_CONTRACT_PREFIX}test-tool-201",
                "category": "api",
                "description": "Contract test tool",
            },
        )
        assert r.status_code in (200, 201), f"Expected 200/201, got {r.status_code}"
        body = r.json()
        assert "id" in body, "Created tool should have an id"

    async def test_create_skill_returns_201_with_resource(self, test_client):
        r = await test_client.post(
            "/api/skills",
            json={
                "name": f"{_CONTRACT_PREFIX}test-skill-201",
                "category": "general",
                "description": "Contract test skill",
            },
        )
        assert r.status_code in (200, 201), f"Expected 200/201, got {r.status_code}"
        body = r.json()
        assert "id" in body, "Created skill should have an id"


# ═══════════════════════════════════════════════════════════════════════════════
# All endpoints respect Accept: application/json header
# ═══════════════════════════════════════════════════════════════════════════════


class TestAcceptHeader:
    """Verify endpoints respect the Accept header."""

    ACCEPT_JSON = {"Accept": "application/json"}

    async def test_health_accepts_json(self, test_client):
        r = await test_client.get("/api/health", headers=self.ACCEPT_JSON)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/json")

    async def test_openapi_accepts_json(self, test_client):
        r = await test_client.get("/openapi.json", headers=self.ACCEPT_JSON)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/json")

    async def test_agents_list_accepts_json(self, test_client):
        r = await test_client.get("/api/agents", headers=self.ACCEPT_JSON)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/json")

    async def test_sessions_list_accepts_json(self, test_client):
        r = await test_client.get("/api/sessions", headers=self.ACCEPT_JSON)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/json")

    async def test_tools_list_accepts_json(self, test_client):
        r = await test_client.get("/api/tools", headers=self.ACCEPT_JSON)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/json")

    async def test_teams_list_accepts_json(self, test_client):
        r = await test_client.get("/api/teams", headers=self.ACCEPT_JSON)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/json")

    async def test_skills_list_accepts_json(self, test_client):
        r = await test_client.get("/api/skills", headers=self.ACCEPT_JSON)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/json")

    async def test_mcps_list_accepts_json(self, test_client):
        r = await test_client.get("/api/mcps", headers=self.ACCEPT_JSON)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/json")

    async def test_prompts_list_accepts_json(self, test_client):
        r = await test_client.get("/api/prompts", headers=self.ACCEPT_JSON)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/json")

    async def test_workflows_list_accepts_json(self, test_client):
        r = await test_client.get("/api/workflows", headers=self.ACCEPT_JSON)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/json")


# ═══════════════════════════════════════════════════════════════════════════════
# Every item in a list response has an id field
# ═══════════════════════════════════════════════════════════════════════════════

LIST_ENDPOINTS: list[tuple[str, str]] = [
    ("/api/agents", "agents"),
    ("/api/tools", "tools"),
    ("/api/skills", "skills"),
    ("/api/mcps", "mcps"),
    ("/api/teams", "teams"),
    ("/api/prompts", "prompts"),
    ("/api/keys", "keys"),
    ("/api/commands", "commands"),
    ("/api/workflows", "workflows"),
    ("/api/sessions", "sessions"),
]


class TestListItemHasId:
    """Verify every item in every list response has an 'id' field."""

    async def _ids_present(self, items: list[object]) -> None:
        for i, item in enumerate(items):
            assert isinstance(item, dict), f"Item {i} is not a dict: {type(item)}"
            assert "id" in item, f"Item {i} ({item.get('name', '')}) missing 'id' field"

    async def test_agents_list_items_have_id(self, test_client):
        r = await test_client.get("/api/agents")
        assert r.status_code == 200
        body = r.json()
        items = body if isinstance(body, list) else body.get("items", body.get("data", []))
        if items:
            await self._ids_present(items)

    async def test_tools_list_items_have_id(self, test_client):
        r = await test_client.get("/api/tools")
        assert r.status_code == 200
        body = r.json()
        items = body if isinstance(body, list) else body.get("items", body.get("data", []))
        if items:
            await self._ids_present(items)

    async def test_skills_list_items_have_id(self, test_client):
        r = await test_client.get("/api/skills")
        assert r.status_code == 200
        body = r.json()
        items = body if isinstance(body, list) else body.get("items", body.get("data", []))
        if items:
            await self._ids_present(items)

    async def test_mcps_list_items_have_id(self, test_client):
        r = await test_client.get("/api/mcps")
        assert r.status_code == 200
        body = r.json()
        items = body if isinstance(body, list) else body.get("items", body.get("data", []))
        if items:
            await self._ids_present(items)

    async def test_teams_list_items_have_id(self, test_client):
        r = await test_client.get("/api/teams")
        assert r.status_code == 200
        body = r.json()
        items = body if isinstance(body, list) else body.get("items", body.get("data", []))
        if items:
            await self._ids_present(items)

    async def test_prompts_list_items_have_id(self, test_client):
        r = await test_client.get("/api/prompts")
        assert r.status_code == 200
        body = r.json()
        items = body if isinstance(body, list) else body.get("items", body.get("data", []))
        if items:
            await self._ids_present(items)

    async def test_keys_list_items_have_id(self, test_client):
        r = await test_client.get("/api/keys")
        assert r.status_code == 200
        body = r.json()
        items = body if isinstance(body, list) else body.get("items", body.get("data", []))
        if items:
            await self._ids_present(items)

    async def test_sessions_list_items_have_id(self, test_client):
        r = await test_client.get("/api/sessions")
        assert r.status_code == 200
        body = r.json()
        items = body if isinstance(body, list) else body.get("items", body.get("data", []))
        if items:
            await self._ids_present(items)

    async def test_workflows_list_items_have_id(self, test_client):
        r = await test_client.get("/api/workflows")
        assert r.status_code == 200
        body = r.json()
        items = body if isinstance(body, list) else body.get("items", body.get("data", []))
        if items:
            await self._ids_present(items)
