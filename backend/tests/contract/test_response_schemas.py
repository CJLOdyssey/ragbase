"""Response schema contract tests — verify field completeness of key endpoints.

Runs against the live backend (contract_client): created resources are
cleaned up right after each check so repeated runs stay idempotent.
"""

import pytest

pytestmark = pytest.mark.integration

# ── Resource namespacing for contract tests ───────────────────────────────────
_CONTRACT_PREFIX = "contract-"


class TestSessionCreateResponseSchema:
    async def test_create_session_response_has_required_fields(self, contract_client):
        r = await contract_client.post(
            "/api/sessions",
            json={"title": f"{_CONTRACT_PREFIX}test-session"},
        )
        assert r.status_code == 201
        body = r.json()
        assert "id" in body, "Missing 'id' field in session create response"
        assert "title" in body, "Missing 'title' field in session create response"
        await contract_client.delete(f"/api/sessions/{body['id']}")


class TestPromptCreateResponseSchema:
    async def test_create_prompt_response_has_required_fields(self, contract_client):
        r = await contract_client.post(
            "/api/prompts",
            json={
                "name": f"{_CONTRACT_PREFIX}test-prompt",
                "content": "测试提示词内容",
                "category": "general",
            },
        )
        assert r.status_code == 201
        body = r.json()
        assert "id" in body, "Missing 'id' field in prompt create response"
        assert "name" in body, "Missing 'name' field in prompt create response"
        await contract_client.delete(f"/api/prompts/{body['id']}")


class TestRunCreateResponseSchema:
    async def test_create_run_response_has_required_fields(self, contract_client):
        r = await contract_client.post(
            "/api/sessions",
            json={"title": f"{_CONTRACT_PREFIX}run-session"},
        )
        if r.status_code != 201:
            pytest.skip("session creation failed — cannot create run")
        session_id = r.json()["id"]
        r = await contract_client.post(
            "/api/runs",
            json={"requirement": "契约测试 run", "session_id": session_id},
        )
        await contract_client.delete(f"/api/sessions/{session_id}")
        assert r.status_code == 200
        body = r.json()
        assert "run_id" in body, "Missing 'run_id' in run create response"
        assert "session_id" in body, "Missing 'session_id' in run create response"
        assert "status" in body, "Missing 'status' in run create response"


# ═══════════════════════════════════════════════════════════════════════════════
# List endpoints return raw arrays
# ═══════════════════════════════════════════════════════════════════════════════


class TestListResponseShape:
    async def test_list_endpoints_return_arrays(self, contract_client):
        for path in ["/api/sessions", "/api/prompts", "/api/models", "/api/keys", "/api/assets"]:
            r = await contract_client.get(path)
            assert r.status_code == 200, f"{path}: expected 200, got {r.status_code}"
            assert isinstance(r.json(), list), f"{path}: expected raw array"


# ═══════════════════════════════════════════════════════════════════════════════
# All endpoints respect Accept: application/json header
# ═══════════════════════════════════════════════════════════════════════════════


class TestAcceptHeader:
    """Verify endpoints respect the Accept header."""

    ACCEPT_JSON = {"Accept": "application/json"}

    async def test_health_accepts_json(self, contract_client):
        r = await contract_client.get("/api/health", headers=self.ACCEPT_JSON)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/json")

    async def test_openapi_accepts_json(self, contract_client):
        r = await contract_client.get("/openapi.json", headers=self.ACCEPT_JSON)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/json")

    async def test_list_endpoints_accept_json(self, contract_client):
        for path in ["/api/sessions", "/api/models", "/api/prompts"]:
            r = await contract_client.get(path, headers=self.ACCEPT_JSON)
            assert r.status_code == 200
            assert r.headers.get("content-type", "").startswith("application/json")


# ═══════════════════════════════════════════════════════════════════════════════
# Every item in a list response has an id field
# ═══════════════════════════════════════════════════════════════════════════════


class TestListItemHasId:
    """Verify every item in every list response has an 'id' field."""

    async def _ids_present(self, items: list[object]) -> None:
        for i, item in enumerate(items):
            assert isinstance(item, dict), f"Item {i} is not a dict: {type(item)}"
            assert "id" in item, f"Item {i} ({item.get('name', '')}) missing 'id' field"

    async def test_sessions_list_items_have_id(self, contract_client):
        r = await contract_client.get("/api/sessions")
        assert r.status_code == 200
        items = r.json()
        if items:
            await self._ids_present(items)

    async def test_prompts_list_items_have_id(self, contract_client):
        r = await contract_client.get("/api/prompts")
        assert r.status_code == 200
        items = r.json()
        if items:
            await self._ids_present(items)

    async def test_keys_list_items_have_id(self, contract_client):
        r = await contract_client.get("/api/keys")
        assert r.status_code == 200
        items = r.json()
        if items:
            await self._ids_present(items)
