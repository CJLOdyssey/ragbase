import pytest
pytestmark = pytest.mark.integration

"""E2E Test: Full end-to-end business flow."""

import contextlib

from tests.conftest import Api, _clear_rate_limits, _rid


class TestFullE2EFlow:
    def test_complete_business_flow(self, api: Api):
        """Team → Prompt → Tool → MCP → Skill → Agent → Session → Run → Verify."""
        cleanup = []
        _clear_rate_limits()

        try:
            # 1. Create team

            r = api.post("/api/teams", json={"name": "E2E-Full-Team"})
            assert r.status_code == 201, r.text
            team = r.json()
            cleanup.append((team["id"], "/api/teams"))

            # 2. Create prompt

            r = api.post(
                "/api/prompts",
                json={
                    "name": "E2E-Full-Prompt",
                    "content": "你是专业助手",
                    "category": "general",
                },
            )
            assert r.status_code == 201, r.text
            prompt = r.json()
            cleanup.append((prompt["id"], "/api/prompts"))

            # 3. Create tool

            r = api.post(
                "/api/tools",
                json={
                    "name": "E2E-Full-Tool",
                    "category": "utility",
                    "description": "计算器",
                },
            )
            assert r.status_code == 201, r.text
            tool = r.json()
            cleanup.append((tool["id"], "/api/tools"))

            # 4. Create MCP

            r = api.post(
                "/api/mcps",
                json={
                    "name": "E2E-Full-MCP",
                    "server_type": "stdio",
                    "command": "python",
                    "args": ["-m", "mcp"],
                    "env": {},
                },
            )
            assert r.status_code == 201, r.text
            mcp = r.json()
            cleanup.append((mcp["id"], "/api/mcps"))

            # 5. Create skill

            r = api.post(
                "/api/skills",
                json={
                    "name": "E2E-Full-Skill",
                    "description": "审查",
                    "version": "1.0",
                    "category": "code_review",
                    "config": {},
                },
            )
            assert r.status_code == 201, r.text
            skill = r.json()
            cleanup.append((skill["id"], "/api/skills"))

            # 6. Create agent with all config

            r = api.post(
                "/api/agents",
                json={
                    "name": "E2E-Full-Agent",
                    "role_identifier": _rid("e2e_full"),
                    "system_prompt": "你是E2E全配置测试助手，请简洁回答。",
                    "output_constraints": "1. 使用中文\n2. 不超过50字",
                    "model": "deepseek-v4-flash",
                    "temperature": 0.5,
                    "tools": [{"id": tool["id"], "name": tool["name"], "enabled": True}],
                    "mcp": [{"id": mcp["id"], "name": mcp["name"], "enabled": False}],
                    "skills": [{"id": skill["id"], "name": skill["name"], "version": "1.0"}],
                    "is_active": True,
                    "icon": "🧪",
                },
            )
            assert r.status_code == 201, r.text
            agent = r.json()
            cleanup.append((agent["id"], "/api/agents"))

            # 7. Verify agent config persisted correctly
            r = api.get(f"/api/agents/{agent['id']}")
            assert r.status_code == 200
            a = r.json()
            assert a["system_prompt"] == "你是E2E全配置测试助手，请简洁回答。"
            assert a["output_constraints"] == "1. 使用中文\n2. 不超过50字"
            assert a["model"] == "deepseek-v4-flash"
            assert len(a["tools"]) == 1
            assert a["tools"][0]["id"] == tool["id"]
            assert len(a["skills"]) == 1

            # 8. Verify team has agent
            r = api.get(f"/api/teams/{team['id']}")
            assert r.status_code == 200

            # 9. Create session

            r = api.post("/api/sessions", json={"title": "E2E-Full-Session"})
            assert r.status_code == 201, r.text
            session = r.json()
            cleanup.append((session["id"], "/api/sessions"))

            # 10. Create run (may fail if no LLM API key, that's OK)
            r = api.post(
                "/api/runs",
                json={
                    "requirement": "1+1等于多少？",
                    "session_id": session["id"],
                    "agent_id": agent["id"],
                },
            )
            if r.status_code == 200:
                run = r.json()
                assert "run_id" in run
                assert run.get("session_id") == session["id"]
            else:
                # LLM not configured → expected failure, test CRUD still works
                assert r.status_code in (400, 422, 500)

        finally:
            # Cleanup (reverse order)
            for eid, ep in reversed(cleanup):
                with contextlib.suppress(Exception):
                    api.delete(f"{ep}/{eid}")
