"""Integration tests for FastAPI REST API routes using in-memory SQLite and TestClient."""
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.unit



class TestApiEndpoints:

    def test_health_check(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "degraded")
        assert "checks" in data
        assert "database" in data["checks"]

    def test_version_endpoint(self, client):
        resp = client.get("/api/version")
        assert resp.status_code == 200
        assert "version" in resp.json()

    def test_metrics_endpoint(self, client):
        resp = client.get("/api/metrics")
        assert resp.status_code == 200

    def test_models_list(self, client):
        resp = client.get("/api/models")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)









    def test_prompts_list(self, client):
        resp = client.get("/api/prompts")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_providers_list(self, client):
        resp = client.get("/api/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert "openai" in data

    def test_versions_list(self, client):
        # resource_type 白名单（A5-04）：仅注册过的类型可查；agent 未注册 → 400
        resp = client.get("/api/versions/agent/test-nonexistent")
        assert resp.status_code == 400
        resp = client.get("/api/versions/prompt/test-nonexistent")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_keys_list(self, client):
        resp = client.get("/api/keys")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)











class TestPromptCRUD:

    def _create_prompt(self, client, name="test-prompt", category="general"):
        payload = {"name": name, "category": category, "content": "You are a helpful assistant."}
        resp = client.post("/api/prompts", json=payload)
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_prompt_create(self, client):
        payload = {"name": "test-prompt", "category": "general", "content": "You are a helpful assistant."}
        resp = client.post("/api/prompts", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["name"] == "test-prompt"

    def test_prompt_update(self, client):
        prompt_id = self._create_prompt(client, "prompt-to-update")
        resp = client.put(f"/api/prompts/{prompt_id}", json={"name": "updated-prompt", "content": "Updated content"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "updated-prompt"
        assert data["content"] == "Updated content"

    def test_prompt_delete(self, client):
        prompt_id = self._create_prompt(client, "prompt-to-delete")
        resp = client.delete(f"/api/prompts/{prompt_id}")
        assert resp.status_code == 204

    def test_prompt_get_nonexistent_returns_404(self, client):
        resp = client.put("/api/prompts/nonexistent-id-99999", json={"name": "nope"})
        assert resp.status_code == 404

    def test_prompt_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/api/prompts/nonexistent-id-99999")
        assert resp.status_code == 404

    def test_prompt_create_empty_body_returns_422(self, client):
        resp = client.post("/api/prompts", json={})
        assert resp.status_code == 422


class TestSessionCRUD:

    USER_HEADERS = {"X-User-ID": "admin"}

    def _create_session(self, client, title="test-session"):
        resp = client.post("/api/sessions", json={"title": title}, headers=self.USER_HEADERS)
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_session_create_and_list(self, client):
        resp = client.post("/api/sessions", json={"title": "test-session"}, headers=self.USER_HEADERS)
        assert resp.status_code == 201
        session_id = resp.json()["id"]
        assert resp.json()["title"] == "test-session"

        resp = client.get("/api/sessions", headers=self.USER_HEADERS)
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()]
        assert session_id in ids

    def test_session_detail(self, client):
        session_id = self._create_session(client, "detail-session")
        resp = client.get(f"/api/sessions/{session_id}", headers=self.USER_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "detail-session"
        assert "runs" in data
        assert "memories" in data

    def test_session_rename(self, client):
        session_id = self._create_session(client, "rename-me")
        resp = client.put(f"/api/sessions/{session_id}", json={"title": "renamed-session"}, headers=self.USER_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["title"] == "renamed-session"

    def test_session_delete(self, client):
        session_id = self._create_session(client, "delete-me")
        resp = client.delete(f"/api/sessions/{session_id}", headers=self.USER_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    def test_session_get_nonexistent_returns_404(self, client):
        resp = client.get("/api/sessions/nonexistent-id-99999", headers=self.USER_HEADERS)
        assert resp.status_code == 404

    def test_session_update_nonexistent_returns_404(self, client):
        resp = client.put("/api/sessions/nonexistent-id-99999", json={"title": "nope"}, headers=self.USER_HEADERS)
        assert resp.status_code == 404

    def test_session_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/api/sessions/nonexistent-id-99999", headers=self.USER_HEADERS)
        assert resp.status_code == 404

    def test_session_rename_empty_body_returns_422(self, client):
        resp = client.put("/api/sessions/nonexistent-id", json={}, headers=self.USER_HEADERS)
        assert resp.status_code == 422


class TestKeyCRUD:

    USER_HEADERS = {"X-User-ID": "admin"}

    def test_key_create(self, client):
        payload = {
            "provider": "openai",
            "capabilities": ["embedding"],
            "label": "test-key",
            "api_key": "sk-test-key-value",
        }
        resp = client.post("/api/keys", json=payload, headers=self.USER_HEADERS)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["provider"] == "openai"

    def test_key_list(self, client):
        resp = client.get("/api/keys", headers=self.USER_HEADERS)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_key_create_empty_body_returns_422(self, client):
        resp = client.post("/api/keys", json={}, headers=self.USER_HEADERS)
        assert resp.status_code == 422



class TestRunBasic:

    def test_create_run(self, client):
        import routers.runs as runs_router

        mock_result = {
            "run_id": "test-run-id-123",
            "session_id": "test-session-id-456",
            "status": "running",
        }
        with patch.object(runs_router.run_service, 'create_run', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_result
            resp = client.post("/api/runs", json={"requirement": "test requirement"}, headers={"X-User-ID": "admin"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["run_id"] == "test-run-id-123"
            assert data["status"] == "running"
            assert data["session_id"] == "test-session-id-456"

    def test_list_runs(self, client):
        import routers.runs as runs_router

        with patch.object(runs_router.run_service, 'list_runs', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [
                {"id": "run-1", "requirement": "test 1", "status": "converged"},
                {"id": "run-2", "requirement": "test 2", "status": "running"},
            ]
            resp = client.get("/api/runs")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0]["id"] == "run-1"


class TestDebugEndpoints:

    def test_debug_health(self, client):
        resp = client.get("/api/debug/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "events_stored" in data
