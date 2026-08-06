"""Shared fixtures for router tests."""
import os
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

os.environ.update({
    "AUTH_MODE": "legacy",
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "REDIS_URL": "redis://localhost:6379/0",
    "KEY_VAULT_SECRET": "0123456789abcdef0123456789abcdef",
    "AUTH_ENABLED": "0",
    "RATE_LIMIT": "9999",
    "CHECKPOINTER_BACKEND": "memory",
})

import core.infra.database as db_mod

if db_mod._async_engine is None:
    _sqlite_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    db_mod._async_engine = _sqlite_engine
if db_mod._async_session_factory is None:
    db_mod._async_session_factory = async_sessionmaker(
        db_mod._async_engine or create_async_engine("sqlite+aiosqlite:///:memory:"),
        expire_on_commit=False,
    )
db_mod.DATABASE_URL = "sqlite+aiosqlite:///:memory:"

from core.app import app
from core.base import Base


@pytest.fixture(autouse=True)
async def _reset_db():
    """Drop and recreate all tables before every test for cross-file isolation.

    All router tests share a single module-level in-memory SQLite engine (one
    per xdist worker), so rows created by one test file persist into the next
    on the same worker. That leaks users/agents/roles across files and causes
    UNIQUE username / role_identifier collisions and mutated seed passwords.
    Mirror the repository tests' pattern (tests/repository/conftest.py): reset
    the schema before each test so every test starts with a clean slate.
    """
    import core.infra.database as db_mod

    engine = db_mod.get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
def client():
    import core.app_lifespan as lifespan_mod

    async def _init_db():
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

    lifespan_mod.init_db = _init_db

    store: dict[str, str] = {}
    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1
    mock_redis.expire.return_value = True
    mock_redis.ping.return_value = True
    mock_redis.publish.return_value = 1
    mock_redis.get.side_effect = lambda k: store.get(k)
    mock_redis.set.side_effect = lambda k, v, *a, **kw: store.update({k: v}) or True
    mock_redis.delete.side_effect = lambda k: store.pop(k, None) or True

    with (
        patch("broker.get_redis", return_value=mock_redis),
        patch("core.app_lifespan.get_redis", return_value=mock_redis),
        patch("routers.auth.login.get_redis", return_value=mock_redis),
        patch("routers.auth.register.get_redis", return_value=mock_redis),
        patch("routers.auth.password.get_redis", return_value=mock_redis),
    ):
        with TestClient(app) as c:
            yield c
