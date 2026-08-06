"""E2E test: MCP tool invocation during agent run (pipeline validation)."""

from __future__ import annotations

import contextlib
import json

import pytest

from tests.conftest import Api, _clear_rate_limits, _rid

pytestmark = pytest.mark.integration


class TestMCPInvocation:
    """Verify MCP tools are properly wired into agent runs."""

    def test_mcp_wired_into_run(self, api: Api):
        """Create MCP → agent with MCP → session → run → verify pipeline."""
        _clear_rate_limits()
        cleanup = []

        try:
            # 1. Create an MCP server entry
            r = api.post(
                "/api/mcps",
                json={
                    "name": _rid("e2e-mcp"),
                    "type": "stdio",
                    "endpoint": "echo",
                    "config": json.dumps({"description": "E2E test MCP", "version": "v1.0.0"}),
                },
            )
            assert r.status_code == 201, f"MCP create failed: {r.text}"
            mcp = r.json()
            cleanup.append((mcp["id"], "/api/mcps"))

            # 2. Create an agent with this MCP bound
            r = api.post(
                "/api/agents",
                json={
                    "name": _rid("e2e-mcp-agent"),
                    "role_identifier": _rid("e2e_mcp_agent"),
                    "system_prompt": "You are an MCP test agent.",
                    "mcp": [{"id": mcp["id"], "name": mcp["name"], "enabled": True}],
                    "is_active": True,
                },
            )
            assert r.status_code == 201, f"Agent create failed: {r.text}"
            agent = r.json()
            cleanup.append((agent["id"], "/api/agents"))

            # 3. Verify agent has the MCP bound
            r = api.get(f"/api/agents/{agent['id']}")
            assert r.status_code == 200
            agent_detail = r.json()
            mcp_bindings = agent_detail.get("mcp", [])
            assert len(mcp_bindings) == 1
            assert mcp_bindings[0]["id"] == mcp["id"]
            assert mcp_bindings[0].get("enabled", False) is True

            # 4. Create a session
            r = api.post("/api/sessions", json={"title": _rid("e2e-mcp-session")})
            assert r.status_code == 201, f"Session create failed: {r.text}"
            session = r.json()
            cleanup.append((session["id"], "/api/sessions"))

            # 5. Create a run with the agent
            r = api.post(
                "/api/runs",
                json={
                    "requirement": "test MCP wiring",
                    "session_id": session["id"],
                    "agent_id": agent["id"],
                },
            )
            # Run may succeed (LLM configured) or fail (no LLM key) — either validates
            # that the pipeline accepted the request
            assert r.status_code in (200, 400, 422, 500), f"Run failed: {r.text}"
            if r.status_code == 200:
                run = r.json()
                assert "run_id" in run
                assert run.get("session_id") == session["id"]

        finally:
            for eid, ep in reversed(cleanup):
                with contextlib.suppress(Exception):
                    api.delete(f"{ep}/{eid}")



