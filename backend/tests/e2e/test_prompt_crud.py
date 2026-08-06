import pytest
pytestmark = pytest.mark.integration

"""E2E Test: Prompt CRUD operations."""

from tests.conftest import Api, _cleanup


class TestPromptCRUD:
    def test_create_prompt(self, api: Api):
        r = api.post(
            "/api/prompts",
            json={
                "name": "E2E-Prompt",
                "content": "审查代码安全性",
                "category": "code_review",
                "tags": ["security"],
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["name"] == "E2E-Prompt"
        _cleanup((body["id"], "/api/prompts"))

    def test_list_prompts(self, api: Api):
        r = api.get("/api/prompts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_update_prompt(self, api: Api):
        r = api.post(
            "/api/prompts",
            json={
                "name": "Old",
                "content": "old",
                "category": "general",
            },
        )
        pid = r.json()["id"]
        r2 = api.put(f"/api/prompts/{pid}", json={"name": "New"})
        assert r2.status_code == 200
        assert r2.json()["name"] == "New"
        _cleanup((pid, "/api/prompts"))

    def test_delete_prompt(self, api: Api):
        r = api.post(
            "/api/prompts",
            json={
                "name": "Del",
                "content": "x",
                "category": "general",
            },
        )
        pid = r.json()["id"]
        r2 = api.delete(f"/api/prompts/{pid}")
        assert r2.status_code in (200, 204)
