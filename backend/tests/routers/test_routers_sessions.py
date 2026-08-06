"""Sessions router tests — merged from test_coverage_boost and test_coverage_gaps."""

import asyncio
import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

import pytest
from starlette.testclient import TestClient

os.environ["AUTH_MODE"] = "legacy"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["KEY_VAULT_SECRET"] = "0123456789abcdef0123456789abcdef"
os.environ["AUTH_ENABLED"] = "0"
os.environ["RATE_LIMIT"] = "9999"
os.environ["CHECKPOINTER_BACKEND"] = "memory"

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import core.infra.database as db_mod

if db_mod._async_engine is None:
    _sqlite_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    db_mod._async_engine = _sqlite_engine
if db_mod._async_session_factory is None:
    db_mod._async_session_factory = async_sessionmaker(
        db_mod._async_engine if db_mod._async_engine is not None else create_async_engine("sqlite+aiosqlite:///:memory:"),
        expire_on_commit=False,
    )
db_mod.DATABASE_URL = "sqlite+aiosqlite:///:memory:"

from core.app import app
from core.base import Base


@pytest.fixture
def client():
    import core.app_lifespan as lifespan_mod

    async def _safe_init_db():
        engine = db_mod.get_async_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        from core.seed import seed_default_roles_and_admin
        await seed_default_roles_and_admin()
        import bcrypt
        from sqlalchemy import select
        from core.infra.database import UserDB, get_session_factory
        factory = get_session_factory()
        async with factory() as session:
            existing = await session.execute(
                select(UserDB).where(UserDB.email == "admin@test.com")
            )
            if not existing.scalar_one_or_none():
                user = UserDB(
                    id="admin-login",
                    username="admin-login",
                    email="admin@test.com",
                    password_hash=bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode(),
                    is_active=True,
                    is_verified=True,
                )
                session.add(user)
                await session.commit()

    lifespan_mod.init_db = _safe_init_db

    store: dict[str, str] = {}

    async def _redis_get(key: str) -> str | None:
        return store.get(key)

    async def _redis_set(key: str, value: str, *args: object, **kwargs: object) -> bool:
        store[key] = value
        return True

    async def _redis_delete(key: str) -> bool:
        store.pop(key, None)
        return True

    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1
    mock_redis.expire.return_value = True
    mock_redis.ping.return_value = True
    mock_redis.publish.return_value = 1
    mock_redis.get.side_effect = _redis_get
    mock_redis.set.side_effect = _redis_set
    mock_redis.delete.side_effect = _redis_delete

    with patch("broker.get_redis", return_value=mock_redis), \
         patch("core.app_lifespan.get_redis", return_value=mock_redis), \
         patch("routers.auth.login.get_redis", return_value=mock_redis), \
         patch("routers.auth.register.get_redis", return_value=mock_redis), \
         patch("routers.auth.password.get_redis", return_value=mock_redis):
        with TestClient(app) as c:
            yield c


class TestSessions:
    """Merged: TestSessions + TestSessionsGaps."""

    # ── List / Create ────────────────────────────────────────────────────

    def test_list_sessions(self, client):
        resp = client.get("/api/sessions", headers={"X-User-ID": "admin"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_sessions_exception(self, client):
        with patch("routers.sessions.get_sessions", new_callable=AsyncMock, side_effect=RuntimeError("db error")):
            resp = client.get("/api/sessions", headers={"X-User-ID": "admin"})
            assert resp.status_code == 500

    def test_create_session(self, client):
        resp = client.post("/api/sessions", json={"title": "new-sess"}, headers={"X-User-ID": "admin"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "new-sess"
        assert "id" in data

    def test_create_session_exception(self, client):
        with patch("routers.sessions.create_session", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            resp = client.post("/api/sessions", json={"title": "x"}, headers={"X-User-ID": "admin"})
            assert resp.status_code == 500

    # ── Get detail ───────────────────────────────────────────────────────

    def test_get_session_detail(self, client):
        resp = client.post("/api/sessions", json={"title": "detail-test"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]
        resp = client.get(f"/api/sessions/{session_id}", headers={"X-User-ID": "admin"})
        assert resp.status_code == 200
        data = resp.json()
        assert "runs" in data
        assert "memories" in data

    def test_get_session_detail_returns_messages_with_thinking(self, client):
        """Session detail must include run.messages with thinking — the frontend
        renders the thinking panel from this field; a stripped response falls
        back to run.requirement/code without thinking."""
        from repository import create_run, save_message

        resp = client.post("/api/sessions", json={"title": "detail-thinking"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]
        run_id = asyncio.run(create_run("打开抖音", session_id=session_id))
        asyncio.run(save_message(run_id, "Agent", "Agent", "已打开抖音", 1, thinking="先想一下再回答"))

        resp = client.get(f"/api/sessions/{session_id}", headers={"X-User-ID": "admin"})
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
        resp = client.get("/api/sessions/nonexistent", headers={"X-User-ID": "admin"})
        assert resp.status_code == 404

    def test_get_session_forbidden(self, client):
        resp = client.post("/api/sessions", json={"title": "owner-session"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]
        resp = client.get(f"/api/sessions/{session_id}", headers={"X-User-ID": "other-user"})
        assert resp.status_code == 403

    def test_get_session_exception(self, client):
        with patch("routers.sessions.get_session", new_callable=AsyncMock, side_effect=RuntimeError("error")):
            resp = client.get("/api/sessions/some-id", headers={"X-User-ID": "admin"})
            assert resp.status_code == 500

    # ── Rename ───────────────────────────────────────────────────────────

    def test_rename_session(self, client):
        resp = client.post("/api/sessions", json={"title": "old-name"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]
        resp = client.put(f"/api/sessions/{session_id}", json={"title": "new-name"}, headers={"X-User-ID": "admin"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "new-name"
        assert resp.json()["status"] == "updated"

    def test_rename_session_not_found(self, client):
        resp = client.put("/api/sessions/nonexistent", json={"title": "x"}, headers={"X-User-ID": "admin"})
        assert resp.status_code == 404

    def test_rename_session_forbidden(self, client):
        resp = client.post("/api/sessions", json={"title": "own"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]
        resp = client.put(f"/api/sessions/{session_id}", json={"title": "new"},
                          headers={"X-User-ID": "other"})
        assert resp.status_code == 403

    def test_rename_session_update_returns_none(self, client):
        resp = client.post("/api/sessions", json={"title": "x"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]
        with patch("routers.sessions.update_session_title", new_callable=AsyncMock, return_value=None):
            resp = client.put(f"/api/sessions/{session_id}", json={"title": "new"},
                              headers={"X-User-ID": "admin"})
            assert resp.status_code == 404

    def test_rename_session_exception(self, client):
        resp = client.post("/api/sessions", json={"title": "x"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]
        with patch("routers.sessions.update_session_title", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            resp = client.put(f"/api/sessions/{session_id}", json={"title": "new"},
                              headers={"X-User-ID": "admin"})
            assert resp.status_code == 500

    # ── Delete ───────────────────────────────────────────────────────────

    def test_delete_session(self, client):
        resp = client.post("/api/sessions", json={"title": "to-delete"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]
        resp = client.delete(f"/api/sessions/{session_id}", headers={"X-User-ID": "admin"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    def test_delete_session_not_found(self, client):
        resp = client.delete("/api/sessions/nonexistent", headers={"X-User-ID": "admin"})
        assert resp.status_code == 404

    def test_delete_session_forbidden(self, client):
        resp = client.post("/api/sessions", json={"title": "own-del"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]
        resp = client.delete(f"/api/sessions/{session_id}", headers={"X-User-ID": "other"})
        assert resp.status_code == 403

    def test_delete_session_returns_false(self, client):
        resp = client.post("/api/sessions", json={"title": "x"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]
        with patch("routers.sessions.delete_session", new_callable=AsyncMock, return_value=False):
            resp = client.delete(f"/api/sessions/{session_id}", headers={"X-User-ID": "admin"})
            assert resp.status_code == 404

    def test_delete_session_exception(self, client):
        resp = client.post("/api/sessions", json={"title": "x"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]
        with patch("routers.sessions.delete_session", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            resp = client.delete(f"/api/sessions/{session_id}", headers={"X-User-ID": "admin"})
            assert resp.status_code == 500

    # ── Memories ─────────────────────────────────────────────────────────

    def test_list_memories(self, client):
        resp = client.post("/api/sessions", json={"title": "mem-test"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]
        resp = client.get(f"/api/sessions/{session_id}/memories", headers={"X-User-ID": "admin"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_memories_session_not_found(self, client):
        resp = client.get("/api/sessions/nonexistent/memories", headers={"X-User-ID": "admin"})
        assert resp.status_code == 404

    def test_list_memories_forbidden(self, client):
        resp = client.post("/api/sessions", json={"title": "mem-own"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]
        resp = client.get(f"/api/sessions/{session_id}/memories", headers={"X-User-ID": "other"})
        assert resp.status_code == 403

    def test_list_memories_exception(self, client):
        with patch("routers.sessions.get_session", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            resp = client.get("/api/sessions/id/memories", headers={"X-User-ID": "admin"})
            assert resp.status_code == 500

    def test_delete_memory_not_found(self, client):
        resp = client.delete("/api/memories/nonexistent", headers={"X-User-ID": "admin"})
        assert resp.status_code == 404

    def test_delete_memory_success(self, client):
        with patch("routers.sessions.delete_memory_entry", new_callable=AsyncMock) as mock_del:
            mock_del.return_value = True
            resp = client.delete("/api/memories/mem-1", headers={"X-User-ID": "admin"})
            assert resp.status_code == 200

    def test_delete_memory_exception(self, client):
        with patch("routers.sessions.delete_memory_entry", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            resp = client.delete("/api/memories/mem-1", headers={"X-User-ID": "admin"})
            assert resp.status_code == 500

    # ── Export memories ──────────────────────────────────────────────────

    def test_export_memories_json(self, client):
        resp = client.post("/api/sessions", json={"title": "export-json"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]
        resp = client.get(f"/api/sessions/{session_id}/memories/export?format=json", headers={"X-User-ID": "admin"})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/json"

    def test_export_memories_markdown(self, client):
        resp = client.post("/api/sessions", json={"title": "export-md"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]
        resp = client.get(f"/api/sessions/{session_id}/memories/export?format=md", headers={"X-User-ID": "admin"})
        assert resp.status_code == 200
        assert "markdown" in resp.headers["content-type"]

    def test_export_memories_markdown_with_memory(self, client):
        resp = client.post("/api/sessions", json={"title": "md-export"}, headers={"X-User-ID": "admin"})
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
            resp = client.get(f"/api/sessions/{session_id}/memories/export?format=md",
                              headers={"X-User-ID": "admin"})
            assert resp.status_code == 200
            assert "markdown" in resp.headers["content-type"]

    def test_export_memories_invalid_format(self, client):
        resp = client.post("/api/sessions", json={"title": "export-bad"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]
        resp = client.get(f"/api/sessions/{session_id}/memories/export?format=csv", headers={"X-User-ID": "admin"})
        assert resp.status_code == 400

    def test_export_memories_session_not_found(self, client):
        resp = client.get("/api/sessions/nonexistent/memories/export?format=json", headers={"X-User-ID": "admin"})
        assert resp.status_code == 404

    def test_export_memories_forbidden(self, client):
        resp = client.post("/api/sessions", json={"title": "exp-own"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]
        resp = client.get(f"/api/sessions/{session_id}/memories/export?format=json",
                          headers={"X-User-ID": "other"})
        assert resp.status_code == 403

    def test_export_memories_exception(self, client):
        with patch("routers.sessions.get_session", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            resp = client.get("/api/sessions/id/memories/export?format=json",
                              headers={"X-User-ID": "admin"})
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
