"""API contract tests — verify schema, status codes, and response shapes."""

import pytest

pytestmark = pytest.mark.integration


class TestOpenAPISchema:
    """Verify the OpenAPI schema is complete and well-formed."""

    async def test_openapi_json_is_accessible(self, test_client):
        r = await test_client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert "openapi" in schema
        assert "paths" in schema

    async def test_schema_contains_expected_routes(self, test_client):
        r = await test_client.get("/openapi.json")
        paths = r.json()["paths"]
        expected = [
            "/api/health",
            "/api/models",
            "/api/agents",
            "/api/tools",
            "/api/skills",
            "/api/mcps",
            "/api/teams",
            "/api/prompts",
            "/api/keys",
            "/api/providers",
            "/api/commands",
            "/api/workflows",
            "/api/sessions",
        ]
        for route in expected:
            assert route in paths, f"Missing route: {route}"


class TestHealthEndpoint:
    async def test_health_returns_200_with_status(self, test_client):
        r = await test_client.get("/api/health")
        assert r.status_code == 200
        body = r.json()
        assert "status" in body
        assert body["status"] in ("healthy", "degraded")


class TestListEndpoints:
    """Verify list endpoints return 200 with array response."""

    async def test_models_returns_array(self, test_client):
        r = await test_client.get("/api/models")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_agents_returns_array(self, test_client):
        r = await test_client.get("/api/agents")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_tools_returns_array(self, test_client):
        r = await test_client.get("/api/tools")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_skills_returns_array(self, test_client):
        r = await test_client.get("/api/skills")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_mcps_returns_array(self, test_client):
        r = await test_client.get("/api/mcps")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_teams_returns_array(self, test_client):
        r = await test_client.get("/api/teams")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_prompts_returns_array(self, test_client):
        r = await test_client.get("/api/prompts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_keys_returns_array(self, test_client):
        r = await test_client.get("/api/keys")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_providers_returns_object(self, test_client):
        r = await test_client.get("/api/providers")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, dict)

    async def test_commands_returns_array(self, test_client):
        r = await test_client.get("/api/commands")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_workflows_returns_array(self, test_client):
        r = await test_client.get("/api/workflows")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestErrorResponses:
    """Verify each endpoint returns proper error codes for invalid requests."""

    async def test_nonexistent_route_returns_404(self, test_client):
        r = await test_client.get("/api/nonexistent-route-xyz")
        assert r.status_code == 404

    async def test_post_agents_without_body_returns_error(self, test_client):
        r = await test_client.post("/api/agents")
        assert r.status_code in (401, 422)

    async def test_nonexistent_agent_detail_returns_404(self, test_client):
        r = await test_client.get("/api/agents/nonexistent-99999")
        assert r.status_code == 404

    async def test_nonexistent_tool_detail_returns_404(self, test_client):
        r = await test_client.get("/api/tools/nonexistent-99999")
        assert r.status_code == 404

    async def test_nonexistent_skill_detail_returns_404(self, test_client):
        r = await test_client.get("/api/skills/nonexistent-99999")
        assert r.status_code == 404

    async def test_nonexistent_session_detail_returns_404(self, test_client):
        r = await test_client.get("/api/sessions/nonexistent-99999")
        assert r.status_code == 404

    async def test_nonexistent_team_detail_returns_404(self, test_client):
        r = await test_client.get("/api/teams/nonexistent-99999")
        assert r.status_code == 404

    async def test_create_session_empty_body_returns_422(self, test_client):
        r = await test_client.post("/api/sessions", json={})
        assert r.status_code == 422

    async def test_create_team_empty_body_returns_422(self, test_client):
        r = await test_client.post("/api/teams", json={})
        assert r.status_code == 422

    async def test_create_tool_empty_body_returns_422(self, test_client):
        r = await test_client.post("/api/tools", json={})
        assert r.status_code == 422

    async def test_create_mcp_extra_fields_ignored_or_error(self, test_client):
        r = await test_client.post("/api/mcps", json={
            "name": "test-mcp-extras",
            "type": "stdio",
            "command": "echo",
            "args": ["hello"],
            "env": {},
            "nonexistent_field": "should_not_be_accepted",
        })
        assert r.status_code in (200, 201, 422)


class TestAuthRequired:
    """Verify that mutation endpoints document auth requirements in the OpenAPI schema."""

    async def test_openapi_has_security_requirements(self, test_client):
        r = await test_client.get("/openapi.json")
        schema = r.json()
        assert "components" in schema
        components = schema["components"]
        assert "securitySchemes" in components, "Missing securitySchemes in OpenAPI spec"
        schemes = components["securitySchemes"]
        assert "OAuth2PasswordBearer" in schemes or "HTTPBearer" in schemes or any(
            "bearer" in name.lower() or "jwt" in name.lower()
            for name in schemes
        ), "No Bearer/JWT auth scheme in OpenAPI spec"

    async def test_agents_delete_requires_auth(self, test_client):
        """DELETE /api/agents/{id} uses Depends(get_current_user) — must be documented."""
        r = await test_client.get("/openapi.json")
        paths = r.json()["paths"]
        if "/api/agents/{agent_id}" in paths:
            delete_op = paths["/api/agents/{agent_id}"].get("delete", {})
            assert "security" in delete_op, (
                "DELETE /api/agents/{agent_id} should document security requirements"
            )

    async def test_critical_endpoints_document_auth(self, test_client):
        """Verify mutation endpoints that should require auth are documented."""
        r = await test_client.get("/openapi.json")
        paths = r.json()["paths"]
        critical_mutations: list[str] = [
            ("post", "/api/agents"),
            ("put", "/api/agents/{agent_id}"),
            ("delete", "/api/agents/{agent_id}"),
        ]
        for method, path in critical_mutations:
            if path in paths:
                operation = paths[path].get(method, {})
                assert "security" in operation, (
                    f"{method.upper()} {path} should document security requirements"
                )


class TestUndocumentedEndpoints:
    """Verify openapi.json paths match the actual registered router paths."""

    async def test_all_router_prefixes_in_openapi(self, test_client):
        r = await test_client.get("/openapi.json")
        paths: dict[str, object] = r.json()["paths"]

        expected_prefixes = [
            "/api/health",
            "/api/models",
            "/api/agents",
            "/api/attachments",
            "/api/commands",
            "/api/keys",
            "/api/mcps",
            "/api/prompts",
            "/api/providers",
            "/api/runs",
            "/api/sessions",
            "/api/skills",
            "/api/teams",
            "/api/tools",
            "/api/versions",
            "/api/workflows",
            "/api/admin",
            "/api/auth",
            "/api/metrics",
            "/api/version",
        ]

        for prefix in expected_prefixes:
            has_prefix = any(p.startswith(prefix) for p in paths)
            assert has_prefix, f"Expected prefix {prefix} not found in openapi.json paths"

    async def test_no_deprecated_routes_in_openapi(self, test_client):
        """Ensure no route is explicitly marked as deprecated unless intended."""
        r = await test_client.get("/openapi.json")
        paths = r.json()["paths"]
        deprecated_paths: list[str] = []
        for path, methods in paths.items():
            for method, operation in methods.items():
                if isinstance(operation, dict) and operation.get("deprecated"):
                    deprecated_paths.append(f"{method.upper()} {path}")
        assert deprecated_paths == [], f"Deprecated routes found: {deprecated_paths}"
