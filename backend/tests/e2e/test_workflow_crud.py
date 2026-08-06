import pytest

pytestmark = pytest.mark.integration

"""E2E Test: Workflow CRUD operations."""

import uuid

from tests.conftest import Api, _cleanup, _rid


class TestWorkflowCRUD:
    """E2E tests for workflow create, list, update, and delete operations."""

    def _create_team(self, api: Api) -> str:
        """Helper: create a team and return its ID."""
        r = api.post("/api/teams", json={"name": f"WF-Team-{uuid.uuid4().hex[:16]}"})
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def _create_agent(self, api: Api) -> str:
        """Helper: create an agent and return its ID."""
        r = api.post(
            "/api/agents",
            json={
                "name": f"WF-Agent-{_rid('wfa')}",
                "role_identifier": f"wf_agent_{uuid.uuid4().hex[:16]}",
                "system_prompt": "workflow test agent",
            },
        )
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def _create_workflow_payload(self, team_id: str, agent_id: str) -> dict:
        """Build a minimal workflow config payload."""
        return {
            "team_id": team_id,
            "name": f"WF-{_rid('wf')}",
            "max_rounds": 3,
            "nodes": [
                {
                    "agent_config_id": agent_id,
                    "role_identifier": "main",
                    "strategy": "generator",
                    "order": 0,
                }
            ],
            "edges": [],
        }

    def test_create_workflow(self, api: Api):
        """POST /api/workflows creates a workflow config."""
        team_id = self._create_team(api)
        agent_id = self._create_agent(api)
        payload = self._create_workflow_payload(team_id, agent_id)

        r = api.post("/api/workflows", json=payload)
        assert r.status_code == 201, r.text
        body = r.json()
        assert "id" in body
        assert body["teamId"] == team_id
        assert body["name"] == payload["name"]
        assert body["maxRounds"] == 3
        assert len(body["nodes"]) == 1
        assert body["nodes"][0]["roleIdentifier"] == "main"
        assert body["nodes"][0]["strategy"] == "generator"

    def test_list_workflows(self, api: Api):
        """GET /api/workflows returns a list."""
        r = api.get("/api/workflows")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_get_workflow_by_team(self, api: Api):
        """GET /api/workflows/teams/{team_id} returns workflow for a team."""
        team_id = self._create_team(api)
        agent_id = self._create_agent(api)
        payload = self._create_workflow_payload(team_id, agent_id)

        r = api.post("/api/workflows", json=payload)
        assert r.status_code == 201, r.text
        wf_id = r.json()["id"]

        r2 = api.get(f"/api/workflows/teams/{team_id}")
        assert r2.status_code == 200
        body = r2.json()
        assert body["teamId"] == team_id
        assert body["id"] == wf_id
        _cleanup((wf_id, "/api/workflows"))

    def test_get_workflow_nonexistent_team(self, api: Api):
        """GET /api/workflows/teams/{fake} returns 404."""
        r = api.get("/api/workflows/teams/nonexistent-team-id-12345")
        assert r.status_code in (404, 400)

    def test_update_workflow(self, api: Api):
        """PUT via POST /api/workflows updates an existing workflow."""
        team_id = self._create_team(api)
        agent_id = self._create_agent(api)
        payload = self._create_workflow_payload(team_id, agent_id)

        r = api.post("/api/workflows", json=payload)
        assert r.status_code == 201, r.text
        wf_id = r.json()["id"]
        _cleanup((wf_id, "/api/workflows"))

        # Update: change name and max_rounds
        payload["id"] = wf_id
        payload["name"] = "Updated-WF-Name"
        payload["max_rounds"] = 10
        r2 = api.post("/api/workflows", json=payload)
        assert r2.status_code == 201, r2.text
        body = r2.json()
        assert body["name"] == "Updated-WF-Name"
        assert body["maxRounds"] == 10

    def test_delete_workflow(self, api: Api):
        """DELETE /api/workflows/{id} removes a workflow."""
        team_id = self._create_team(api)
        agent_id = self._create_agent(api)
        payload = self._create_workflow_payload(team_id, agent_id)

        r = api.post("/api/workflows", json=payload)
        assert r.status_code == 201, r.text
        wf_id = r.json()["id"]

        r2 = api.delete(f"/api/workflows/{wf_id}")
        assert r2.status_code == 200
        assert r2.json()["status"] == "deleted"

    def test_delete_workflow_nonexistent(self, api: Api):
        """DELETE /api/workflows/{fake} returns error."""
        r = api.delete("/api/workflows/nonexistent-wf-id-99999")
        assert r.status_code in (404, 400)

    def test_create_workflow_missing_fields(self, api: Api):
        """POST /api/workflows with missing required fields returns 422."""
        r = api.post("/api/workflows", json={})
        assert r.status_code == 422

    def test_create_workflow_missing_nodes(self, api: Api):
        """POST /api/workflows without nodes returns 422."""
        r = api.post(
            "/api/workflows",
            json={
                "team_id": "some-team",
                "name": "No-Nodes",
                "edges": [],
            },
        )
        assert r.status_code == 422

    def test_workflow_multi_node(self, api: Api):
        """Create a workflow with multiple nodes and an edge."""
        team_id = self._create_team(api)
        agent_id1 = self._create_agent(api)
        agent_id2 = self._create_agent(api)

        payload = {
            "team_id": team_id,
            "name": f"Multi-Node-WF-{_rid('wf')}",
            "max_rounds": 5,
            "nodes": [
                {
                    "agent_config_id": agent_id1,
                    "role_identifier": "planner",
                    "strategy": "generator",
                    "order": 0,
                },
                {
                    "agent_config_id": agent_id2,
                    "role_identifier": "reviewer",
                    "strategy": "generator",
                    "order": 1,
                },
            ],
            "edges": [
                {
                    "from_node_id": "planner",
                    "to_node_id": "reviewer",
                    "is_default": True,
                    "priority": 0,
                }
            ],
        }

        r = api.post("/api/workflows", json=payload)
        assert r.status_code == 201, r.text
        body = r.json()
        assert len(body["nodes"]) == 2
        assert len(body["edges"]) == 1
        _cleanup((body["id"], "/api/workflows"))
