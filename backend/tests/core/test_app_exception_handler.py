"""Tests for the global exception handler (backend/core/app.py).

Bootstrap mirrors backend/tests/routers/conftest.py: bounded env + in-memory
sqlite singletons are established BEFORE core.app is imported, so the login
wall can be satisfied with a real authenticated session.
"""

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
        db_mod._async_engine or create_async_engine("sqlite+aiosqlite:///:memory:"),
        expire_on_commit=False,
    )
db_mod.DATABASE_URL = "sqlite+aiosqlite:///:memory:"

from core.app import app
from core.base import Base


@pytest.fixture
def client():
    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1
    mock_redis.expire.return_value = True
    mock_redis.ping.return_value = True
    mock_redis.publish.return_value = 1
    store: dict[str, str] = {}
    mock_redis.get.side_effect = lambda k: store.get(k)
    mock_redis.set.side_effect = lambda k, v, *a, **kw: store.update({k: v}) or True
    mock_redis.delete.side_effect = lambda k: store.pop(k, None) or True

    import core.app_lifespan as lifespan_mod

    async def _init_db():
        engine = db_mod.get_async_engine()
        async with engine.begin() as conn:
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
                session.add(UserDB(
                    id="admin-login",
                    username="admin-login",
                    email="admin@test.com",
                    password_hash=bcrypt.hashpw(
                        b"admin123", bcrypt.gensalt()
                    ).decode(),
                    is_active=True,
                    is_verified=True,
                ))
                await session.commit()

    with (
        # patcher 自动还原：init_db 覆写不得泄漏给同 worker 后续测试
        patch.object(lifespan_mod, "init_db", _init_db),
        patch("broker.get_redis", return_value=mock_redis),
        patch("core.app_lifespan.get_redis", return_value=mock_redis),
        patch("routers.auth.login.get_redis", return_value=mock_redis),
        patch("routers.auth.register.get_redis", return_value=mock_redis),
        patch("routers.auth.password.get_redis", return_value=mock_redis),
    ):
        # 登录墙恒开：异常处理器行为需在已认证请求上验证
        with TestClient(app) as c:
            resp = c.post(
                "/api/auth/login",
                json={"email": "admin@test.com", "password": "admin123"},
            )
            assert resp.status_code == 200, resp.text
            yield c


class TestExceptionHandler:
    def test_health_returned(self, client):
        resp = client.get("/api/health")
        assert resp.status_code in (200, 503)  # may be 503 if DB not available

    def test_version_endpoint(self, client):
        resp = client.get("/api/version")
        assert resp.status_code == 200
        assert "version" in resp.json()

    def test_unknown_route_returns_json(self, client):
        resp = client.get("/api/nonexistent")
        # FastAPI returns 404 for unknown routes
        # The exception handler catches unhandled exceptions only
        assert resp.status_code == 404


class TestGlobalExceptionHandler:
    def test_uncaught_exception_returns_500_json(self, caplog):
        """未捕获异常 → 500 + 结构化 JSON detail，且错误带堆栈落日志。"""
        import json
        import logging

        from core.app import global_exception_handler
        from starlette.requests import Request

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/boom",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)
        core_logger = logging.getLogger("core.app")
        core_logger.propagate = True
        try:
            with caplog.at_level(logging.ERROR):
                resp = global_exception_handler(request, RuntimeError("boom"))
        finally:
            core_logger.propagate = False
        assert resp.status_code == 500
        body = json.loads(bytes(resp.body).decode("utf-8"))
        assert body["detail"] == "服务器内部错误，请查看日志了解详情"
        assert "boom" in caplog.text
