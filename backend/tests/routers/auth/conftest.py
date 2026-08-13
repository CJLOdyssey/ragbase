"""Shared fixtures for auth router tests — extracted from test_routers_auth.py."""

import os
from unittest.mock import AsyncMock, patch

import bcrypt
import pytest
from starlette.testclient import TestClient

# ── Environment setup (must happen before app import) ─────────────────────
os.environ["AUTH_MODE"] = "legacy"
os.environ["DEV_MODE"] = "1"  # auth cookies non-secure so TestClient jar sends them over http
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["KEY_VAULT_SECRET"] = "0123456789abcdef0123456789abcdef"
os.environ["AUTH_ENABLED"] = "0"
os.environ["RATE_LIMIT"] = "9999"
os.environ["CHECKPOINTER_BACKEND"] = "memory"

import core.infra.database as db_mod
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

_sqlite_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
if db_mod._async_engine is None:
    db_mod._async_engine = _sqlite_engine
if db_mod._async_session_factory is None:
    db_mod._async_session_factory = async_sessionmaker(_sqlite_engine, expire_on_commit=False)
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
        # Create roles and users with explicit IDs for legacy mode compatibility.
        # Use raw seeding (not seed_default_roles_and_admin) so admin user gets
        # id="admin" matching CurrentUser() defaults in legacy auth mode.
        from core.infra.database import (
            RoleDB,
            UserDB,
            UserRoleDB,
        )
        from sqlalchemy import select

        async with db_mod._async_session_factory() as session:  # type: ignore[arg-type]
            for role_data in [
                ("role-admin", "admin", {"all": True}),
                ("role-member", "member", {"read": True}),
            ]:
                existing = await session.execute(
                    select(RoleDB).where(RoleDB.name == role_data[1])
                )
                if not existing.scalar_one_or_none():
                    session.add(RoleDB(id=role_data[0], name=role_data[1], permissions=role_data[2]))
            await session.flush()

            admin_role = (
                await session.execute(select(RoleDB).where(RoleDB.name == "admin"))
            ).scalar_one_or_none()

            for user_data in [
                {"id": "admin", "email": "admin@example.com"},
                {"id": "admin-login", "email": "admin@test.com"},
            ]:
                user = (
                    await session.execute(select(UserDB).where(UserDB.id == user_data["id"]))
                ).scalar_one_or_none()
                if user is None:
                    user = UserDB(
                        id=user_data["id"],
                        username=user_data["id"],
                        email=user_data["email"],
                        password_hash=bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode(),
                        is_active=True,
                        is_verified=True,
                    )
                    session.add(user)
                    await session.flush()
                    if admin_role:
                        session.add(UserRoleDB(user_id=user.id, role_id=admin_role.id))
                elif not bcrypt.checkpw(b"admin123", user.password_hash.encode()):
                    # Self-heal: the router-level _reset_db autouse fixture can
                    # occasionally not run under xdist worksteal, leaving a
                    # leftover user (e.g. from a register test) with a different
                    # password that would turn login into 401. Re-seed the
                    # password so login tests stay hermetic.
                    user.password_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
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
