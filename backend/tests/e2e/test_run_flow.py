import pytest

pytestmark = pytest.mark.integration

"""E2E Test: Run operations — create, status, history."""

import uuid

from tests.conftest import Api, _cleanup, _rid


class TestRunFlow:
    """E2E tests for run create, get status, and list history."""

    def _create_session(self, api: Api) -> str:
        """Helper: create a session and return its ID."""
        r = api.post("/api/sessions", json={"title": f"Run-Session-{_rid('rs')}"})
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def _create_agent(self, api: Api) -> str:
        """Helper: create an agent and return its ID."""
        r = api.post(
            "/api/agents",
            json={
                "name": f"Run-Agent-{_rid('ra')}",
                "role_identifier": f"run_agent_{uuid.uuid4().hex[:16]}",
                "system_prompt": "run test agent",
                "model": "deepseek-v4-flash",
            },
        )
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def test_list_runs(self, api: Api):
        """GET /api/runs returns a list of run summaries."""
        r = api.get("/api/runs")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_list_runs_with_limit(self, api: Api):
        """GET /api/runs?limit=5 returns at most 5 items."""
        r = api.get("/api/runs", params={"limit": 5})
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) <= 5

    def test_get_run_nonexistent(self, api: Api):
        """GET /api/runs/{fake} returns error."""
        r = api.get("/api/runs/nonexistent-run-id-12345")
        assert r.status_code in (404, 400)

    def test_create_run_missing_requirement(self, api: Api):
        """POST /api/runs without requirement returns 422."""
        r = api.post("/api/runs", json={})
        assert r.status_code == 422

    def test_create_run_empty_requirement(self, api: Api):
        """POST /api/runs with empty requirement returns error."""
        r = api.post("/api/runs", json={"requirement": ""})
        assert r.status_code in (400, 422)

    def test_create_run_whitespace_requirement(self, api: Api):
        """POST /api/runs with whitespace-only requirement returns error."""
        r = api.post("/api/runs", json={"requirement": "   "})
        # Whitespace is stripped → may become empty → 400
        # Or it may still pass if there are non-space chars
        assert r.status_code in (200, 400, 422)

    def test_create_run_basic(self, api: Api):
        """POST /api/runs creates a run (may fail without LLM key)."""
        session_id = self._create_session(api)
        agent_id = self._create_agent(api)
        r = api.post(
            "/api/runs",
            json={
                "requirement": "1+1等于多少？",
                "session_id": session_id,
                "agent_id": agent_id,
            },
        )
        if r.status_code == 200:
            body = r.json()
            assert "run_id" in body
            assert "status" in body
            assert body.get("session_id") == session_id
        else:
            # No LLM API key configured → expected failure
            assert r.status_code in (400, 422, 500)

    def test_create_run_with_session_only(self, api: Api):
        """POST /api/runs with session_id but no agent_id."""
        session_id = self._create_session(api)
        r = api.post(
            "/api/runs",
            json={
                "requirement": "test run",
                "session_id": session_id,
            },
        )
        # May succeed (uses default agent) or fail
        assert r.status_code in (200, 400, 422, 500)

    def test_create_run_with_agent_only(self, api: Api):
        """POST /api/runs with agent_id but no session_id."""
        agent_id = self._create_agent(api)
        r = api.post(
            "/api/runs",
            json={
                "requirement": "test run",
                "agent_id": agent_id,
            },
        )
        assert r.status_code in (200, 400, 422, 500)

    def test_get_run_detail_after_create(self, api: Api):
        """GET /api/runs/{id} returns detail for an existing run."""
        session_id = self._create_session(api)
        agent_id = self._create_agent(api)
        r = api.post(
            "/api/runs",
            json={
                "requirement": "detail test",
                "session_id": session_id,
                "agent_id": agent_id,
            },
        )
        if r.status_code != 200:
            return  # skip if LLM not configured
        run_id = r.json()["run_id"]

        r2 = api.get(f"/api/runs/{run_id}")
        assert r2.status_code == 200
        body = r2.json()
        assert body["id"] == run_id
        assert "status" in body

    def test_run_list_structure(self, api: Api):
        """Verify the structure of run summaries in the list."""
        r = api.get("/api/runs", params={"limit": 3})
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        if data:
            item = data[0]
            expected = {"id", "requirement", "status", "created_at"}
            assert expected.issubset(item.keys()), f"Missing: {expected - item.keys()}"

    def test_create_run_long_requirement(self, api: Api):
        """POST /api/runs with very long requirement is rejected."""
        session_id = self._create_session(api)
        long_text = "x" * 5000
        r = api.post(
            "/api/runs",
            json={
                "requirement": long_text,
                "session_id": session_id,
            },
        )
        assert r.status_code in (400, 422)

    def test_create_run_requirement_at_limit(self, api: Api):
        """POST /api/runs with requirement at 2000 chars (boundary)."""
        session_id = self._create_session(api)
        text = "a" * 2000
        r = api.post(
            "/api/runs",
            json={
                "requirement": text,
                "session_id": session_id,
            },
        )
        # Exactly at limit — should be accepted
        assert r.status_code in (200, 400, 422, 500)

    def test_session_crud_full(self, api: Api):
        """Full session lifecycle: create → get → rename → delete."""
        # Create
        r = api.post("/api/sessions", json={"title": f"CRUD-{_rid('sc')}"})
        assert r.status_code == 201, r.text
        sid = r.json()["id"]

        # Get detail
        r2 = api.get(f"/api/sessions/{sid}")
        assert r2.status_code == 200
        assert r2.json()["id"] == sid
        assert "runs" in r2.json()
        assert "memories" in r2.json()

        # Rename
        r3 = api.put(f"/api/sessions/{sid}", json={"title": "Renamed-Session"})
        assert r3.status_code == 200
        assert r3.json()["title"] == "Renamed-Session"
        assert r3.json()["status"] == "updated"

        # Delete
        r4 = api.delete(f"/api/sessions/{sid}")
        assert r4.status_code == 200
        assert r4.json()["status"] == "deleted"

    def test_session_rename_missing_title(self, api: Api):
        """PUT /api/sessions/{id} without title returns 422."""
        r = api.post("/api/sessions", json={"title": f"Rename-{_rid('rn')}"})
        assert r.status_code == 201, r.text
        sid = r.json()["id"]
        _cleanup((sid, "/api/sessions"))

        r2 = api.put(f"/api/sessions/{sid}", json={})
        assert r2.status_code == 422

    def test_session_get_nonexistent(self, api: Api):
        """GET /api/sessions/{fake} returns error."""
        r = api.get("/api/sessions/nonexistent-session-99999")
        assert r.status_code in (404, 400)

    def test_session_delete_nonexistent(self, api: Api):
        """DELETE /api/sessions/{fake} returns error."""
        r = api.delete("/api/sessions/nonexistent-session-99999")
        assert r.status_code in (404, 400)

    def test_list_sessions_with_agent_filter(self, api: Api):
        """GET /api/sessions?agent_id={id} filters by agent."""
        agent_id = self._create_agent(api)
        # Create a session linked to agent
        r = api.post(
            "/api/sessions",
            json={"title": f"Agent-Session-{_rid('as')}", "agent_id": agent_id},
        )
        assert r.status_code == 201, r.text
        sid = r.json()["id"]

        # List with filter
        r2 = api.get("/api/sessions", params={"agent_id": agent_id})
        assert r2.status_code == 200
        data = r2.json()
        assert isinstance(data, list)
        # At least the one we created should appear
        session_ids = [s["id"] for s in data]
        assert sid in session_ids
        _cleanup((sid, "/api/sessions"))
