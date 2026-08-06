"""Runs router tests — merged from test_coverage_boost, test_coverage_gaps, test_remaining_coverage."""

import os
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


class TestRuns:
    """Merged: TestRuns + TestRunsGaps + TestRunsRemainingGaps."""

    # ── Create run ───────────────────────────────────────────────────────

    def test_create_run_empty_requirement(self, client):
        resp = client.post("/api/runs", json={"requirement": ""}, headers={"X-User-ID": "admin"})
        assert resp.status_code == 422

    def test_create_run_whitespace_only(self, client):
        resp = client.post("/api/runs", json={"requirement": "   "}, headers={"X-User-ID": "admin"})
        assert resp.status_code == 400

    def test_create_run_max_length(self, client):
        resp = client.post("/api/runs", json={
            "requirement": "x" * 20000
        }, headers={"X-User-ID": "admin"})
        assert resp.status_code == 422

    @patch("routers.runs.load_config")
    def test_create_run_max_config_length(self, mock_config, client):
        mock_cfg = MagicMock()
        mock_cfg.max_requirement_length = 10
        mock_config.return_value = mock_cfg
        resp = client.post("/api/runs", json={
            "requirement": "x" * 20
        }, headers={"X-User-ID": "admin"})
        assert resp.status_code == 400

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_create_run_success(self, mock_service, client):
        mock_service.create_run = AsyncMock(return_value={
            "run_id": "r-1", "status": "running", "session_id": "s-1",
        })
        resp = client.post("/api/runs", json={"requirement": "build a website"}, headers={"X-User-ID": "admin"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == "r-1"
        assert data["status"] == "running"

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_create_run_value_error(self, mock_service, client):
        mock_service.create_run = AsyncMock(side_effect=ValueError("bad input"))
        resp = client.post("/api/runs", json={"requirement": "test"}, headers={"X-User-ID": "admin"})
        assert resp.status_code == 400

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_create_run_http_exception_reraise(self, mock_service, client):
        from fastapi import HTTPException
        mock_service.create_run = AsyncMock(side_effect=HTTPException(status_code=400, detail="bad"))
        resp = client.post("/api/runs", json={"requirement": "test"}, headers={"X-User-ID": "admin"})
        assert resp.status_code == 400

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_create_run_generic_error(self, mock_service, client):
        mock_service.create_run = AsyncMock(side_effect=RuntimeError("something broke"))
        resp = client.post("/api/runs", json={"requirement": "test"}, headers={"X-User-ID": "admin"})
        assert resp.status_code == 500

    # ── Get run detail ───────────────────────────────────────────────────

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_get_run_detail_found(self, mock_service, client):
        mock_service.get_run = AsyncMock(return_value={
            "id": "r-1", "requirement": "test", "status": "converged",
            "session_id": "s-1", "messages": [],
        })
        resp = client.get("/api/runs/r-1")
        assert resp.status_code == 200

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_get_run_detail_not_found(self, mock_service, client):
        mock_service.get_run = AsyncMock(return_value=None)
        resp = client.get("/api/runs/nonexistent")
        assert resp.status_code == 404

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_get_run_detail_http_exception(self, mock_service, client):
        from fastapi import HTTPException
        mock_service.get_run = AsyncMock(side_effect=HTTPException(status_code=404, detail="not found"))
        resp = client.get("/api/runs/notfound")
        assert resp.status_code == 404

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_get_run_detail_error(self, mock_service, client):
        mock_service.get_run = AsyncMock(side_effect=RuntimeError("db error"))
        resp = client.get("/api/runs/r-error")
        assert resp.status_code == 500

    # ── List runs ────────────────────────────────────────────────────────

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_list_runs_success(self, mock_service, client):
        mock_service.list_runs = AsyncMock(return_value=[
            {"id": "r-1", "requirement": "t1", "status": "converged", "session_id": "s1"},
        ])
        resp = client.get("/api/runs")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_list_runs_error(self, mock_service, client):
        mock_service.list_runs = AsyncMock(side_effect=RuntimeError("error"))
        resp = client.get("/api/runs")
        assert resp.status_code == 500

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_list_runs_exception(self, mock_service, client):
        mock_service.list_runs = AsyncMock(side_effect=RuntimeError("db error"))
        resp = client.get("/api/runs?limit=10")
        assert resp.status_code == 500

    # ── Model tests ──────────────────────────────────────────────────────

    def test_run_request_validation(self):
        from routers.runs import RunRequest
        req = RunRequest(requirement="hello")
        assert req.requirement == "hello"
        assert req.session_id is None

    def test_run_request_camel_case_aliases(self):
        from routers.runs import RunRequest
        req = RunRequest(requirement="test", sessionId="s1", keyId="k1")
        assert req.session_id == "s1"
        assert req.key_id == "k1"

    def test_run_response_model(self):
        from routers.runs import RunResponse
        resp = RunResponse(run_id="r1", status="running")
        assert resp.run_id == "r1"

    def test_run_response_optional_fields(self):
        from routers.runs import RunResponse
        resp = RunResponse(run_id="r1", status="running", session_id="s1")
        assert resp.session_id == "s1"
