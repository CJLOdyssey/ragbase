"""Observability router tests share the routers' auth posture: real login.

The debug endpoints sit behind AuthMiddleware, and login is rate-limited,
so this package mirrors backend/tests/routers/conftest.py: bounded env,
in-memory sqlite bootstrap, per-test schema reset, redis mocks, and a
client fixture pre-authenticated as admin-login.
"""
import contextlib
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
    db_mod._async_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
if db_mod._async_session_factory is None:
    db_mod._async_session_factory = async_sessionmaker(
        db_mod._async_engine,
        expire_on_commit=False,
    )
db_mod.DATABASE_URL = "sqlite+aiosqlite:///:memory:"

from core.app import app
from core.base import Base


async def _reset_schema() -> None:
    """Drop and recreate all tables (awaitable — runs inside the app loop)."""
    engine = db_mod.get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(autouse=True)
async def _reset_db():
    """Fresh schema per test (mirrors routers/conftest isolation contract)."""
    await _reset_schema()


def _build_logged_in_client(raise_server_exceptions: bool):
    """Shared login flow for both normal and 500-capturing clients."""
    import core.app_lifespan as lifespan_mod

    async def _init_db():
        await _reset_schema()
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
                    password_hash=bcrypt.hashpw(
                        b"admin123", bcrypt.gensalt()
                    ).decode(),
                    is_active=True,
                    is_verified=True,
                )
                session.add(user)
                await session.commit()

        # admin-login 授予 admin 角色：登录身份与 RBAC 依赖（require_role）对齐，
        # 与 backend/tests/routers/conftest.py 保持一致。
        from core.infra.database import RoleDB, UserRoleDB

        async with factory() as session:
            admin_role = (
                await session.execute(select(RoleDB).where(RoleDB.name == "admin"))
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

    ctx = (
        # patcher 自动还原：init_db 覆写不得泄漏给同 worker 后续测试
        patch.object(lifespan_mod, "init_db", _init_db),
        patch("broker.get_redis", return_value=mock_redis),
        patch("core.app_lifespan.get_redis", return_value=mock_redis),
        patch("routers.auth.login.get_redis", return_value=mock_redis),
        patch("routers.auth.register.get_redis", return_value=mock_redis),
        patch("routers.auth.password.get_redis", return_value=mock_redis),
    )

    class _LoggedIn:
        def __enter__(self):
            self.stack = contextlib.ExitStack()
            for p in ctx:
                self.stack.enter_context(p)
            self.tc = TestClient(app, raise_server_exceptions=raise_server_exceptions)
            c = self.stack.enter_context(self.tc)
            resp = c.post(
                "/api/auth/login",
                json={"email": "admin@test.com", "password": "admin123"},
            )
            assert resp.status_code == 200, resp.text
            return c

        def __exit__(self, *exc):
            return self.stack.__exit__(*exc)

    return _LoggedIn()


@pytest.fixture
def client():
    """常规客户端：服务端异常由 app 转 500 响应。"""
    with _build_logged_in_client(raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def client_strict():
    """严格客户端：服务端异常直接抛出而非转 500。"""
    with _build_logged_in_client(raise_server_exceptions=True) as c:
        yield c
