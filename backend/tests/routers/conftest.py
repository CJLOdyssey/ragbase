"""Shared fixtures for router tests."""
import os
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

os.environ.update({
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "REDIS_URL": "redis://localhost:6379/0",
    "KEY_VAULT_SECRET": "0123456789abcdef0123456789abcdef",
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
            # Self-contained reset: don't rely on the _reset_db autouse
            # fixture (not reliably ordered under xdist worksteal).
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        from core.seed import seed_default_roles_and_admin
        await seed_default_roles_and_admin()
        import bcrypt
        from core.infra.database import (
            RoleDB,
            UserDB,
            UserRoleDB,
            get_session_factory,
        )
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

        # admin-login 授予 admin 角色：登录身份与 RBAC 依赖（require_role）对齐
        async with factory() as session:
            admin_role = (
                await session.execute(
                    select(RoleDB).where(RoleDB.name == "admin")
                )
            ).scalar_one_or_none()
            admin_login = (
                await session.execute(
                    select(UserDB).where(UserDB.id == "admin-login")
                )
            ).scalar_one_or_none()
            if admin_role is not None and admin_login is not None:
                already = await session.execute(
                    select(UserRoleDB).where(
                        UserRoleDB.user_id == "admin-login",
                        UserRoleDB.role_id == admin_role.id,
                    )
                )
                if not already.scalar_one_or_none():
                    session.add(
                        UserRoleDB(user_id="admin-login", role_id=admin_role.id)
                    )
                    await session.commit()

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
        # patcher 自动还原：init_db 覆写不得泄漏给同 worker 后续测试
        patch.object(lifespan_mod, "init_db", _init_db),
        patch("broker.get_redis", return_value=mock_redis),
        patch("core.app_lifespan.get_redis", return_value=mock_redis),
        patch("routers.auth.login.get_redis", return_value=mock_redis),
        patch("routers.auth.register.get_redis", return_value=mock_redis),
        patch("routers.auth.password.get_redis", return_value=mock_redis),
    ):
        with TestClient(app) as c:
            # 认证已无 legacy 旁路：通过真实登录取得 httpOnly JWT cookie，
            # 后续请求以 admin-login 身份通过 AuthMiddleware。
            resp = c.post(
                "/api/auth/login",
                json={"email": "admin@test.com", "password": "admin123"},
            )
            assert resp.status_code == 200, resp.text
            yield c


SECOND_USER_ID = "second-login"


async def _ensure_second_user() -> None:
    """Create the cross-user test identity if absent."""
    import bcrypt
    from core.infra.database import UserDB, get_session_factory
    from sqlalchemy import select

    factory = get_session_factory()
    async with factory() as session:
        existing = await session.execute(
            select(UserDB).where(UserDB.id == SECOND_USER_ID)
        )
        if not existing.scalar_one_or_none():
            session.add(
                UserDB(
                    id=SECOND_USER_ID,
                    username=SECOND_USER_ID,
                    email="second@test.com",
                    password_hash=bcrypt.hashpw(
                        b"second123", bcrypt.gensalt()
                    ).decode(),
                    is_active=True,
                    is_verified=True,
                )
            )
            await session.commit()


@pytest.fixture
def other_user_headers(client):
    """Authorization header authenticating as a second real user.

    跨用户隔离用例用：同一 client（cookie 为主身份），对单请求以
    Bearer <second user> 覆盖身份，中间件按 header 优先取 token。
    """
    import os

    from auth.auth_jwt import create_token

    client.portal.call(_ensure_second_user)
    secret = os.environ["AUTH_SECRET"]
    token = create_token(SECOND_USER_ID, secret)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def anonymous_headers(client):
    """Bearer token 指向不存在的用户 → 中间件标记 invalid → 匿名语义。"""
    import os

    from auth.auth_jwt import create_token

    secret = os.environ["AUTH_SECRET"]
    token = create_token("ghost-user-not-in-db", secret)
    return {"Authorization": f"Bearer {token}"}
