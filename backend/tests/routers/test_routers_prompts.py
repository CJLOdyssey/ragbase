"""Prompts router tests — merged from test_coverage_boost, test_coverage_gaps, test_remaining_coverage."""

import os
import asyncio
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


class TestPrompts:
    """Merged: TestPrompts + TestPromptsGaps + TestPromptsRemainingGaps."""

    # ── CRUD basics ──────────────────────────────────────────────────────

    def test_list_prompts(self, client):
        resp = client.get("/api/prompts")
        assert resp.status_code == 200

    def test_list_prompts_by_category(self, client):
        resp = client.get("/api/prompts?category=general")
        assert resp.status_code == 200

    def test_create_prompt(self, client):
        resp = client.post("/api/prompts", json={
            "name": "test-prompt", "category": "general", "content": "Be helpful."
        })
        assert resp.status_code == 201

    def test_create_prompt_with_description(self, client):
        resp = client.post("/api/prompts", json={
            "name": "desc-prompt", "description": "用途说明", "category": "general", "content": "Be helpful."
        })
        assert resp.status_code == 201
        assert resp.json()["description"] == "用途说明"

    def test_list_prompts_include_description(self, client):
        client.post("/api/prompts", json={
            "name": "list-desc-prompt", "description": "desc-1", "category": "general", "content": "x"
        })
        resp = client.get("/api/prompts")
        assert resp.status_code == 200
        assert all("description" in p for p in resp.json())

    def test_update_prompt(self, client):
        resp = client.post("/api/prompts", json={
            "name": "upd-prompt", "category": "general", "content": "Original."
        })
        prompt_id = resp.json()["id"]
        resp = client.put(f"/api/prompts/{prompt_id}", json={"name": "updated"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "updated"

    def test_update_prompt_description(self, client):
        resp = client.post("/api/prompts", json={
            "name": "upd-desc-prompt", "description": "old", "category": "general", "content": "Original."
        })
        prompt_id = resp.json()["id"]
        resp = client.put(f"/api/prompts/{prompt_id}", json={"description": "new desc"})
        assert resp.status_code == 200
        assert resp.json()["description"] == "new desc"

    def test_update_prompt_not_found(self, client):
        resp = client.put("/api/prompts/nonexistent", json={"name": "x"})
        assert resp.status_code == 404

    def test_delete_prompt(self, client):
        resp = client.post("/api/prompts", json={
            "name": "del-prompt", "category": "general", "content": "Delete me."
        })
        prompt_id = resp.json()["id"]
        resp = client.delete(f"/api/prompts/{prompt_id}")
        assert resp.status_code == 204

    def test_delete_prompt_not_found(self, client):
        resp = client.delete("/api/prompts/nonexistent")
        assert resp.status_code == 404

    # ── Exception handler paths ──────────────────────────────────────────

    def test_list_prompts_exception(self, client):
        with patch("routers.prompts.get_prompts_as_dicts", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            resp = client.get("/api/prompts")
            assert resp.status_code == 500

    def test_create_prompt_exception(self, client):
        with patch("routers.prompts.create_prompt", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            resp = client.post("/api/prompts", json={"name": "x", "category": "c", "content": "y"})
            assert resp.status_code == 500

    def test_update_prompt_exception(self, client):
        with patch("routers.prompts.update_prompt", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            resp = client.put("/api/prompts/t", json={"name": "x"})
            assert resp.status_code == 500

    def test_delete_prompt_exception(self, client):
        with patch("repository.get_prompts", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            resp = client.delete("/api/prompts/t")
            assert resp.status_code == 500

    # ── Edge cases ───────────────────────────────────────────────────────

    def test_snapshot_prompt_item_not_found(self, client):
        from routers.prompts import _snapshot_prompt
        with patch("repository.prompts.get_prompt", new_callable=AsyncMock, return_value=None), \
             patch("repository.snapshot_helper.with_session", new_callable=AsyncMock) as mock_ws:
            async def capture_call(fn, **kwargs):
                await fn(MagicMock(), "prompt", "p-1")
            mock_ws.side_effect = capture_call
            asyncio.run(_snapshot_prompt("p-1"))

    def test_edit_prompt_generic_exception(self, client):
        resp = client.post("/api/prompts", json={
            "name": "exc-prompt", "category": "general", "content": "x"
        })
        prompt_id = resp.json()["id"]
        with patch("routers.prompts.update_prompt", new_callable=AsyncMock, side_effect=Exception("err")):
            resp = client.put(f"/api/prompts/{prompt_id}", json={"name": "y"})
            assert resp.status_code == 500

    def test_delete_prompt_generic_exception(self, client):
        resp = client.post("/api/prompts", json={
            "name": "del-exc-prompt", "category": "general", "content": "x"
        })
        prompt_id = resp.json()["id"]
        with patch("repository.get_prompts", new_callable=AsyncMock, side_effect=Exception("err")):
            resp = client.delete(f"/api/prompts/{prompt_id}")
            assert resp.status_code == 500
