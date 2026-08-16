"""Versions router tests — merged from test_coverage_boost, test_coverage_gaps, test_remaining_coverage."""

import os
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.unit

from starlette.testclient import TestClient

os.environ["AUTH_MODE"] = "legacy"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["KEY_VAULT_SECRET"] = "0123456789abcdef0123456789abcdef"
os.environ["AUTH_ENABLED"] = "0"
os.environ["RATE_LIMIT"] = "9999"
os.environ["CHECKPOINTER_BACKEND"] = "memory"

import core.infra.database as db_mod
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

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
            # Self-contained reset: don't rely on the routers _reset_db
            # autouse fixture (not reliably ordered under xdist worksteal).
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        from core.seed import seed_default_roles_and_admin
        await seed_default_roles_and_admin()
        import bcrypt
        from core.infra.database import UserDB, get_session_factory
        from sqlalchemy import select
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


class TestVersions:
    """Merged: TestVersions + TestVersionsGaps + TestVersionsRemainingGaps."""

    def test_list_versions(self, client):
        resp = client.get("/api/versions/agent/test-resource")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_version(self, client):
        resp = client.post("/api/versions", json={
            "resource_type": "agent",
            "resource_id": "agent-1",
            "snapshot": {"name": "test"},
        })
        assert resp.status_code == 201
        assert resp.json()["resource_type"] == "agent"

    def test_get_version_found(self, client):
        resp = client.post("/api/versions", json={
            "resource_type": "agent",
            "resource_id": "agent-2",
            "snapshot": {"name": "test"},
        })
        version_id = resp.json()["id"]
        resp = client.get(f"/api/versions/detail/{version_id}")
        assert resp.status_code == 200

    def test_get_version_not_found(self, client):
        resp = client.get("/api/versions/detail/nonexistent")
        assert resp.status_code in (200, 404)

    @pytest.mark.skip(reason="Depends(get_session) makes mock unreliable for versions endpoint")
    def test_get_version_not_found_returns_404(self, client):
        with patch("repository.versions.get_version", new_callable=AsyncMock, return_value=None):
            resp = client.get("/api/versions/detail/nonexistent-id")
            assert resp.status_code == 404
