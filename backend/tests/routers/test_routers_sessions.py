"""Sessions router tests — merged from test_coverage_boost and test_coverage_gaps."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit



class TestSessions:
    """Merged: TestSessions + TestSessionsGaps."""

    # ── List / Create ────────────────────────────────────────────────────

    def test_list_sessions(self, client):
        resp = client.get("/api/sessions")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_sessions_exception(self, client):
        with patch("routers.sessions.get_sessions", new_callable=AsyncMock, side_effect=RuntimeError("db error")):
            resp = client.get("/api/sessions")
            assert resp.status_code == 500

    def test_list_sessions_login_wall_401_anonymous(self, client):
        """登录墙恒开：完全无令牌（清空 cookie）列表 → 401 而非 200 []。"""
        saved = dict(client.cookies)
        client.cookies.clear()
        try:
            resp = client.get("/api/sessions")
        finally:
            client.cookies.update(saved)
        assert resp.status_code == 401

    def test_create_session(self, client):
        resp = client.post("/api/sessions", json={"title": "new-sess"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "new-sess"
        assert "id" in data

    def test_create_session_exception(self, client):
        with patch("routers.sessions.create_session", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            resp = client.post("/api/sessions", json={"title": "x"})
            assert resp.status_code == 500

    # ── Get detail ───────────────────────────────────────────────────────

    def test_get_session_detail(self, client):
        resp = client.post("/api/sessions", json={"title": "detail-test"})
        session_id = resp.json()["id"]
        resp = client.get(f"/api/sessions/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "runs" in data
        assert "memories" in data

    def test_get_session_detail_returns_messages_with_thinking(self, client):
        """Session detail must include run.messages with thinking — the frontend
        renders the thinking panel from this field; a stripped response falls
        back to run.requirement/code without thinking."""
        from repository import create_run, save_message

        resp = client.post("/api/sessions", json={"title": "detail-thinking"})
        session_id = resp.json()["id"]
        run_id = asyncio.run(create_run("打开抖音", session_id=session_id))
        asyncio.run(save_message(run_id, "Agent", "Agent", "已打开抖音", 1, thinking="先想一下再回答"))

        resp = client.get(f"/api/sessions/{session_id}")
        assert resp.status_code == 200
        runs = resp.json()["runs"]
        assert len(runs) == 1
        messages = runs[0].get("messages", [])
        # The run requirement is prepended as a synthetic user message so the
        # user's input renders in the conversation (see _with_requirement_message).
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "打开抖音"
        assert messages[1]["content"] == "已打开抖音"
        assert messages[1]["thinking"] == "先想一下再回答"

    def test_get_session_not_found(self, client):
        resp = client.get("/api/sessions/nonexistent")
        assert resp.status_code == 404

    def test_get_session_forbidden(self, client, other_user_headers):
        resp = client.post("/api/sessions", json={"title": "owner-session"})
        session_id = resp.json()["id"]
        resp = client.get(f"/api/sessions/{session_id}", headers=other_user_headers)
        assert resp.status_code == 403

    def test_get_session_exception(self, client):
        with patch("routers.sessions.get_session", new_callable=AsyncMock, side_effect=RuntimeError("error")):
            resp = client.get("/api/sessions/some-id")
            assert resp.status_code == 500

    # ── Rename ───────────────────────────────────────────────────────────

    def test_rename_session(self, client):
        resp = client.post("/api/sessions", json={"title": "old-name"})
        session_id = resp.json()["id"]
        resp = client.put(f"/api/sessions/{session_id}", json={"title": "new-name"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "new-name"
        assert resp.json()["status"] == "updated"

    def test_rename_session_not_found(self, client):
        resp = client.put("/api/sessions/nonexistent", json={"title": "x"})
        assert resp.status_code == 404

    def test_rename_session_forbidden(self, client, other_user_headers):
        resp = client.post("/api/sessions", json={"title": "own"})
        session_id = resp.json()["id"]
        resp = client.put(f"/api/sessions/{session_id}", json={"title": "new"},
                          headers=other_user_headers)
        assert resp.status_code == 403

    def test_rename_session_update_returns_none(self, client):
        resp = client.post("/api/sessions", json={"title": "x"})
        session_id = resp.json()["id"]
        with patch("routers.sessions.update_session_title", new_callable=AsyncMock, return_value=None):
            resp = client.put(f"/api/sessions/{session_id}", json={"title": "new"})
            assert resp.status_code == 404

    def test_rename_session_exception(self, client):
        resp = client.post("/api/sessions", json={"title": "x"})
        session_id = resp.json()["id"]
        with patch("routers.sessions.update_session_title", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            resp = client.put(f"/api/sessions/{session_id}", json={"title": "new"})
            assert resp.status_code == 500

    # ── Pin ──────────────────────────────────────────────────────────────

    def test_pin_session(self, client):
        resp = client.post("/api/sessions", json={"title": "p"})
        session_id = resp.json()["id"]
        resp = client.put(f"/api/sessions/{session_id}/pin", json={"is_pinned": True})
        assert resp.status_code == 200
        assert resp.json()["is_pinned"] is True

    def test_pin_session_unpin(self, client):
        resp = client.post("/api/sessions", json={"title": "p"})
        session_id = resp.json()["id"]
        client.put(f"/api/sessions/{session_id}/pin", json={"is_pinned": True})
        resp = client.put(f"/api/sessions/{session_id}/pin", json={"is_pinned": False})
        assert resp.status_code == 200
        assert resp.json()["is_pinned"] is False

    def test_pin_session_not_found(self, client):
        resp = client.put("/api/sessions/nonexistent/pin", json={"is_pinned": True})
        assert resp.status_code == 404

    def test_pin_session_forbidden(self, client, other_user_headers):
        resp = client.post("/api/sessions", json={"title": "own"})
        session_id = resp.json()["id"]
        resp = client.put(f"/api/sessions/{session_id}/pin", json={"is_pinned": True},
                          headers=other_user_headers)
        assert resp.status_code == 403

    # ── Delete ───────────────────────────────────────────────────────────

    def test_delete_session(self, client):
        resp = client.post("/api/sessions", json={"title": "to-delete"})
        session_id = resp.json()["id"]
        resp = client.delete(f"/api/sessions/{session_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    def test_delete_session_not_found(self, client):
        resp = client.delete("/api/sessions/nonexistent")
        assert resp.status_code == 404

    def test_delete_session_forbidden(self, client, other_user_headers):
        resp = client.post("/api/sessions", json={"title": "own-del"})
        session_id = resp.json()["id"]
        resp = client.delete(f"/api/sessions/{session_id}", headers=other_user_headers)
        assert resp.status_code == 403

    def test_delete_session_returns_false(self, client):
        resp = client.post("/api/sessions", json={"title": "x"})
        session_id = resp.json()["id"]
        with patch("routers.sessions.delete_session", new_callable=AsyncMock, return_value=False):
            resp = client.delete(f"/api/sessions/{session_id}")
            assert resp.status_code == 404

    def test_delete_session_exception(self, client):
        resp = client.post("/api/sessions", json={"title": "x"})
        session_id = resp.json()["id"]
        with patch("routers.sessions.delete_session", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            resp = client.delete(f"/api/sessions/{session_id}")
            assert resp.status_code == 500

    # ── Memories ─────────────────────────────────────────────────────────

    def test_list_memories(self, client):
        resp = client.post("/api/sessions", json={"title": "mem-test"})
        session_id = resp.json()["id"]
        resp = client.get(f"/api/sessions/{session_id}/memories")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_memories_session_not_found(self, client):
        resp = client.get("/api/sessions/nonexistent/memories")
        assert resp.status_code == 404

    def test_list_memories_forbidden(self, client, other_user_headers):
        resp = client.post("/api/sessions", json={"title": "mem-own"})
        session_id = resp.json()["id"]
        resp = client.get(f"/api/sessions/{session_id}/memories", headers=other_user_headers)
        assert resp.status_code == 403

    def test_list_memories_exception(self, client):
        with patch("routers.sessions.get_session", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            resp = client.get("/api/sessions/id/memories")
            assert resp.status_code == 500

    def test_delete_memory_not_found(self, client):
        resp = client.delete("/api/memories/nonexistent")
        assert resp.status_code == 404

    def test_delete_memory_success(self, client):
        with (
            patch("routers.sessions.get_memory_entry", new_callable=AsyncMock) as mock_get,
            patch("routers.sessions.get_session", new_callable=AsyncMock) as mock_sess,
            patch("routers.sessions.delete_memory_entry", new_callable=AsyncMock) as mock_del,
        ):
            mock_get.return_value = MagicMock(session_id="sess-1")
            mock_sess.return_value = MagicMock(user_id="admin-login")
            mock_del.return_value = True
            resp = client.delete("/api/memories/mem-1")
            assert resp.status_code == 200
            mock_del.assert_awaited_once_with("mem-1")

    def test_delete_memory_forbidden_other_user(self, client, other_user_headers):
        with (
            patch("routers.sessions.get_memory_entry", new_callable=AsyncMock) as mock_get,
            patch("routers.sessions.get_session", new_callable=AsyncMock) as mock_sess,
            patch("routers.sessions.delete_memory_entry", new_callable=AsyncMock) as mock_del,
        ):
            mock_get.return_value = MagicMock(session_id="sess-1")
            mock_sess.return_value = MagicMock(user_id="owner-elsewhere")
            resp = client.delete("/api/memories/mem-1", headers=other_user_headers)
            assert resp.status_code == 403
            mock_del.assert_not_awaited()

    def test_delete_memory_exception(self, client):
        with (
            patch("routers.sessions.get_memory_entry", new_callable=AsyncMock) as mock_get,
            patch("routers.sessions.get_session", new_callable=AsyncMock) as mock_sess,
            patch("routers.sessions.delete_memory_entry", new_callable=AsyncMock, side_effect=RuntimeError("err")),
        ):
            mock_get.return_value = MagicMock(session_id="sess-1")
            mock_sess.return_value = MagicMock(user_id="admin-login")
            resp = client.delete("/api/memories/mem-1")
            assert resp.status_code == 500

    # ── Export memories ──────────────────────────────────────────────────

    def test_export_memories_json(self, client):
        resp = client.post("/api/sessions", json={"title": "export-json"})
        session_id = resp.json()["id"]
        resp = client.get(f"/api/sessions/{session_id}/memories/export?format=json")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/json"

    def test_export_memories_markdown(self, client):
        resp = client.post("/api/sessions", json={"title": "export-md"})
        session_id = resp.json()["id"]
        resp = client.get(f"/api/sessions/{session_id}/memories/export?format=md")
        assert resp.status_code == 200
        assert "markdown" in resp.headers["content-type"]

    def test_export_memories_markdown_with_memory(self, client):
        resp = client.post("/api/sessions", json={"title": "md-export"})
        session_id = resp.json()["id"]
        with patch("routers.sessions.get_session_memories", new_callable=AsyncMock) as mock_mems:
            m = MagicMock()
            m.id = "m1"
            m.agent_role = "pm"
            m.content_type = "pm_document"
            m.summary = "Test summary"
            m.details = "Test details"
            m.created_at = datetime.now(UTC)
            mock_mems.return_value = [m]
            resp = client.get(f"/api/sessions/{session_id}/memories/export?format=md")
            assert resp.status_code == 200
            assert "markdown" in resp.headers["content-type"]

    def test_export_memories_invalid_format(self, client):
        resp = client.post("/api/sessions", json={"title": "export-bad"})
        session_id = resp.json()["id"]
        resp = client.get(f"/api/sessions/{session_id}/memories/export?format=csv")
        assert resp.status_code == 400

    def test_export_memories_session_not_found(self, client):
        resp = client.get("/api/sessions/nonexistent/memories/export?format=json")
        assert resp.status_code == 404

    def test_export_memories_forbidden(self, client, other_user_headers):
        resp = client.post("/api/sessions", json={"title": "exp-own"})
        session_id = resp.json()["id"]
        resp = client.get(f"/api/sessions/{session_id}/memories/export?format=json",
                          headers=other_user_headers)
        assert resp.status_code == 403

    def test_export_memories_exception(self, client):
        with patch("routers.sessions.get_session", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            resp = client.get("/api/sessions/id/memories/export?format=json")
            assert resp.status_code == 500

    # ── Model tests ──────────────────────────────────────────────────────

    def test_session_create_request_model(self):
        from routers.sessions import SessionCreateRequest
        req = SessionCreateRequest(title="test")
        assert req.title == "test"

    def test_session_update_request_model(self):
        from routers.sessions import SessionUpdateRequest
        req = SessionUpdateRequest(title="new title")
        assert req.title == "new title"
