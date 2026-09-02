"""API contract tests — verify schema, status codes, and response shapes.

Covers the ragbase route set (auth/keys/models/providers/prompts/sessions/
runs/versions/assets/attachments + observability). Routes are integration-
marked: they run against the live backend and skip when it is unreachable.
"""

import httpx
import pytest

pytestmark = pytest.mark.integration

#: ragbase 实际注册的业务路由前缀（与 core/app.py 的 include_router 对齐）。
EXPECTED_PREFIXES = [
    "/api/health",
    "/api/version",
    "/api/metrics",
    "/api/models",
    "/api/keys",
    "/api/providers",
    "/api/prompts",
    "/api/versions",
    "/api/sessions",
    "/api/runs",
    "/api/attachments",
    "/api/assets",
    "/api/auth",
    "/api/debug",
    "/api/monitoring",
    "/api/feedback",
    "/api/retrieval-logs",
    "/api/knowledge-bases",
    "/api/admin",
]

#: ragbase 已裁剪模块的路由——契约测试必须断言其不存在（死路由回归防护）。
CUT_PREFIXES = [
    "/api/agents",
    "/api/tools",
    "/api/skills",
    "/api/mcps",
    "/api/teams",
    "/api/workflows",
    "/api/commands",
]


class TestOpenAPISchema:
    """Verify the OpenAPI schema is complete and well-formed."""

    async def test_openapi_json_is_accessible(self, contract_client):
        r = await contract_client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert "openapi" in schema
        assert "paths" in schema

    async def test_schema_contains_expected_routes(self, contract_client):
        r = await contract_client.get("/openapi.json")
        paths = r.json()["paths"]
        for prefix in EXPECTED_PREFIXES:
            assert any(p.startswith(prefix) for p in paths), f"Missing prefix {prefix}"

    async def test_schema_excludes_cut_routes(self, contract_client):
        """SPEC 4.5 裁剪边界：被裁模块的路由不得复活。"""
        r = await contract_client.get("/openapi.json")
        paths = r.json()["paths"]
        for prefix in CUT_PREFIXES:
            assert not any(p.startswith(prefix) for p in paths), (
                f"Cut prefix {prefix} still registered"
            )


class TestHealthEndpoint:
    async def test_health_returns_200_with_status(self, contract_client):
        r = await contract_client.get("/api/health")
        assert r.status_code == 200
        body = r.json()
        assert "status" in body
        assert body["status"] in ("healthy", "degraded")

    async def test_version_returns_version(self, contract_client):
        r = await contract_client.get("/api/version")
        assert r.status_code == 200
        assert "version" in r.json()


class TestListEndpoints:
    """Verify list endpoints return 200 with array response."""

    async def test_models_returns_array(self, contract_client):
        r = await contract_client.get("/api/models")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_sessions_returns_array(self, contract_client):
        r = await contract_client.get("/api/sessions")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_prompts_returns_array(self, contract_client):
        r = await contract_client.get("/api/prompts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_keys_returns_array(self, contract_client):
        r = await contract_client.get("/api/keys")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_providers_returns_object(self, contract_client):
        r = await contract_client.get("/api/providers")
        assert r.status_code == 200
        assert isinstance(r.json(), dict)

    async def test_assets_returns_array(self, contract_client):
        r = await contract_client.get("/api/assets")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestErrorResponses:
    """Verify each endpoint returns proper error codes for invalid requests."""

    async def test_nonexistent_route_returns_404(self, contract_client):
        r = await contract_client.get("/api/nonexistent-route-xyz")
        assert r.status_code == 404

    async def test_nonexistent_session_detail_returns_404(self, contract_client):
        r = await contract_client.get("/api/sessions/nonexistent-99999")
        assert r.status_code == 404

    async def test_nonexistent_prompt_detail_returns_404(self, contract_client):
        # prompts 无 GET 详情路由（仅 PUT/DELETE），用 DELETE 验证 404
        r = await contract_client.delete("/api/prompts/nonexistent-99999")
        assert r.status_code == 404

    async def test_nonexistent_run_detail_returns_404(self, contract_client):
        r = await contract_client.get("/api/runs/nonexistent-99999")
        assert r.status_code == 404

    async def test_create_session_empty_body_returns_201(self, contract_client):
        """session 的 title 有默认值（"新对话"），空 body 合法 → 201。"""
        r = await contract_client.post("/api/sessions", json={})
        assert r.status_code == 201
        body = r.json()
        assert body["title"] == "新对话"
        await contract_client.delete(f"/api/sessions/{body['id']}")

    async def test_create_prompt_empty_body_returns_422(self, contract_client):
        r = await contract_client.post("/api/prompts", json={})
        assert r.status_code == 422


class TestAuthRequired:
    """Verify that mutation endpoints require authentication."""

    async def test_models_without_token_returns_401(self, contract_client):
        """不带 token 访问业务 API → 401（AuthMiddleware 生效）。

        注意 httpx 会合并 client 级 headers（pop 请求级副本无效），
        因此用独立的匿名 client 发请求。
        """
        from tests.contract.conftest import BASE_URL

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10) as anon:
            r = await anon.get("/api/models")
        assert r.status_code == 401

    async def test_openapi_has_security_requirements(self, contract_client):
        """OpenAPI 应声明认证方案。

        ragbase 用全局 AuthMiddleware + JWT/cookie 认证（无 per-endpoint
        Depends security）。custom_openapi() 在 core/app.py 中手动声明
        Bearer scheme，确保 Swagger UI 显示"Authorize"按钮。
        """
        r = await contract_client.get("/openapi.json")
        schema = r.json()
        components = schema.get("components", {})
        schemes = components.get("securitySchemes", {})
        assert schemes, "OpenAPI securitySchemes 为空 — custom_openapi() 可能未生效"
        assert any(
            "bearer" in name.lower() or "jwt" in name.lower() or "oauth" in name.lower()
            for name in schemes
        ), "No Bearer/JWT auth scheme in OpenAPI spec"


class TestUndocumentedEndpoints:
    """Verify openapi.json paths match the actual registered router paths."""

    async def test_no_deprecated_routes_in_openapi(self, contract_client):
        r = await contract_client.get("/openapi.json")
        paths = r.json()["paths"]
        deprecated_paths: list[str] = []
        for path, methods in paths.items():
            for method, operation in methods.items():
                if isinstance(operation, dict) and operation.get("deprecated"):
                    deprecated_paths.append(f"{method.upper()} {path}")
        assert deprecated_paths == [], f"Deprecated routes found: {deprecated_paths}"
