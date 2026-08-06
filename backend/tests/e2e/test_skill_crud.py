import pytest
pytestmark = pytest.mark.integration

"""E2E Test: Skill CRUD operations."""

from tests.conftest import Api, _cleanup


class TestSkillCRUD:
    def test_create_skill(self, api: Api):
        r = api.post(
            "/api/skills",
            json={
                "name": "E2E-Skill",
                "description": "自动代码审查",
                "version": "1.0.0",
                "category": "code_review",
                "config": {"rules": ["security"]},
                "is_active": True,
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["name"] == "E2E-Skill"
        _cleanup((body["id"], "/api/skills"))

    def test_list_skills(self, api: Api):
        r = api.get("/api/skills")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_update_skill(self, api: Api):
        r = api.post(
            "/api/skills",
            json={
                "name": "Old",
                "description": "x",
                "version": "1.0",
                "category": "general",
                "config": {},
            },
        )
        sid = r.json()["id"]
        r2 = api.put(f"/api/skills/{sid}", json={"name": "New"})
        assert r2.status_code == 200
        assert r2.json()["name"] == "New"
        _cleanup((sid, "/api/skills"))

    def test_delete_skill(self, api: Api):
        r = api.post(
            "/api/skills",
            json={
                "name": "Del",
                "description": "x",
                "version": "1.0",
                "category": "general",
                "config": {},
            },
        )
        sid = r.json()["id"]
        r2 = api.delete(f"/api/skills/{sid}")
        assert r2.status_code in (200, 204)
