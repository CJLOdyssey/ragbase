"""Shared fixtures and helpers for E2E tests."""

import contextlib
import os
import string
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Force a clean test environment BEFORE any core module is imported.
# core/infra/database.py reads DATABASE_URL (and other vars) at import time;
# a polluted DATABASE_URL from the host shell (e.g. opencode's own
# skill-tracker.db) would otherwise leak into every test worker.
os.environ.update({
    "AUTH_MODE": "legacy",
    "AUTH_ENABLED": "0",
    # auth 流程（register/login）无条件签发 token（_create_auth_response），
    # 空 AUTH_SECRET 会让 PyJWT>=2.12 抛 InvalidKeyError。测试统一给足长密钥。
    "AUTH_SECRET": "test-secret-0123456789abcdef0123456789",
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "REDIS_URL": "redis://localhost:6379/0",
    "KEY_VAULT_SECRET": "0123456789abcdef0123456789abcdef",
    "RATE_LIMIT": "9999",
    "CHECKPOINTER_BACKEND": "memory",
    "DATABASE_POOL_SIZE": "0",
})

from _global_state import capture_global_state, patch_test_globals, restore_global_state
from core.infra.database import Base  # type: ignore[attr-defined]
from core.infra.redis_sentinel import (
    create_redis as _original_create_redis,  # noqa: F401 — saved before test_client patches it
)

_base = Path(__file__).parent.parent
if str(_base) not in sys.path:
    sys.path.insert(0, str(_base))

# Alias backend.X → X so mock patches like "broker.get_redis" resolve
import importlib as _il

import backend as _backend_mod

_backend_src = _base / 'src'
for _p in _backend_src.iterdir():
    if _p.is_dir() and (_p / '__init__.py').exists() and not _p.name.startswith('_'):
        _mod = _il.import_module(_p.name)
        sys.modules[f'backend.{_p.name}'] = _mod
        setattr(_backend_mod, _p.name, _mod)

# Register the requirement coverage plugin
from .requirement_coverage import (  # noqa: F401
    pytest_addoption,
    pytest_collection_modifyitems,
    pytest_configure,
    pytest_runtest_makereport,
    pytest_sessionfinish,
)

# flaky_test may be unavailable in merge/test contexts — import gracefully
try:
    from conftest_flaky import flaky_test  # noqa: F401
except (ImportError, SyntaxError):
    def flaky_test(**kwargs):  # type: ignore[no-redef]
        """No-op fallback when conftest_flaky is unavailable."""
        return lambda fn: fn

BASE = os.environ.get("E2E_BASE_URL", "http://localhost:8082")

# Test user credentials for rbac mode
TEST_EMAIL = "e2e@test.com"
TEST_PASSWORD = "Test@1234"


def _rid(prefix: str = "test") -> str:
    suffix = uuid.uuid4().hex[:8]
    clean_suffix = "".join(c for c in suffix if c in string.ascii_lowercase)
    clean_prefix = "".join(c for c in prefix if c in string.ascii_lowercase + "_")
    result = f"{clean_prefix}_{clean_suffix}" if clean_suffix else f"{clean_prefix}_x"
    return result


def _clear_rate_limits() -> None:
    try:
        out = subprocess.run(
            ["docker", "exec", "ragbase-redis", "redis-cli", "-n", "0", "KEYS", "ratelimit:*"],
            capture_output=True, text=True, timeout=5,
        )
        if out.stdout.strip():
            keys = out.stdout.strip().split("\n")
            subprocess.run(
                ["docker", "exec", "ragbase-redis", "redis-cli", "-n", "0", "DEL"] + keys,
                capture_output=True, timeout=5,
            )
    except Exception:
        pass


_TOKEN_CACHE: str | None = None


def _obtain_token() -> str | None:
    """Obtain a Bearer token for rbac mode.

    Tries POST /api/auth/login first. If that fails (user not yet
    registered), runs the full register flow using docker exec to
    read the verification code from Redis. Caches the token globally
    so the flow executes at most once per session.
    """
    global _TOKEN_CACHE
    if _TOKEN_CACHE is not None:
        return _TOKEN_CACHE

    c = httpx.Client(base_url=BASE, timeout=15)
    try:
        cfg = c.get("/api/auth/config").json()
        if cfg.get("mode") != "rbac":
            return None

        resp = c.post("/api/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
        if resp.status_code == 200:
            _TOKEN_CACHE = resp.json()["access_token"]
            return _TOKEN_CACHE

        # Login failed → register new user
        _clear_rate_limits()
        _delete_redis("auth:verify:e2e@test.com")
        c.post("/api/auth/send-register-code", json={"email": TEST_EMAIL})
        codes = _read_redis("auth:verify:e2e@test.com")
        code = codes[0] if codes else None
        if code:
            resp = c.post(
                "/api/auth/register",
                json={"email": TEST_EMAIL, "code": code, "password": TEST_PASSWORD},
            )
            if resp.status_code == 201:
                _TOKEN_CACHE = resp.json()["access_token"]
                return _TOKEN_CACHE
            resp = c.post("/api/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
            if resp.status_code == 200:
                _TOKEN_CACHE = resp.json()["access_token"]
                return _TOKEN_CACHE
    except Exception:
        pass
    finally:
        c.close()

    # Mark failure so we don't retry on every test
    _TOKEN_CACHE = ""
    return None


def _attach_auth(client: httpx.Client) -> None:
    token = _obtain_token()
    if token:
        client.headers.update({"Authorization": f"Bearer {token}"})


def _cleanup(*ids_and_endpoints: tuple[str, str]) -> None:
    c = httpx.Client(base_url=BASE, timeout=10)
    _attach_auth(c)
    for eid, ep in ids_and_endpoints:
        with contextlib.suppress(Exception):
            c.delete(f"{ep}/{eid}")
    c.close()


def _read_redis(pattern: str) -> list[str]:
    """Read values from Redis matching a key pattern (via docker exec)."""
    try:
        out = subprocess.run(
            ["docker", "exec", "ragbase-redis", "redis-cli", "-n", "0", "KEYS", pattern],
            capture_output=True, text=True, timeout=5,
        )
        if not out.stdout.strip():
            return []
        keys = out.stdout.strip().split("\n")
        vals = subprocess.run(
            ["docker", "exec", "ragbase-redis", "redis-cli", "-n", "0", "MGET"] + keys,
            capture_output=True, text=True, timeout=5,
        )
        return [v for v in vals.stdout.strip().split("\n") if v]
    except Exception:
        return []


def _delete_redis(pattern: str) -> None:
    """Delete Redis keys matching a pattern (via docker exec)."""
    try:
        out = subprocess.run(
            ["docker", "exec", "ragbase-redis", "redis-cli", "-n", "0", "KEYS", pattern],
            capture_output=True, text=True, timeout=5,
        )
        if out.stdout.strip():
            subprocess.run(
                ["docker", "exec", "ragbase-redis", "redis-cli", "-n", "0", "DEL"]
                + out.stdout.strip().split("\n"),
                capture_output=True, timeout=5,
            )
    except Exception:
        pass


class Api:
    def __init__(self, base: str = BASE):
        self.client = httpx.Client(base_url=base, timeout=30)

    def get(self, path: str, **kw: Any) -> httpx.Response:
        return self.client.get(path, **kw)

    def post(self, path: str, json: object = None, **kw: Any) -> httpx.Response:
        return self.client.post(path, json=json, **kw)

    def put(self, path: str, json: object = None, **kw: Any) -> httpx.Response:
        return self.client.put(path, json=json, **kw)

    def delete(self, path: str, **kw: Any) -> httpx.Response:
        return self.client.delete(path, **kw)

    def close(self) -> None:
        self.client.close()


@pytest.fixture
def api() -> Any:
    a = Api()
    _attach_auth(a.client)
    yield a
    a.close()


@pytest.fixture(scope="session")
def event_loop() -> Any:
    """Session-scoped event loop for async fixtures."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def _guard_global_singletons() -> Any:
    """Restore process-global singletons mutated during a single test.

    Managed overwriters already restore via ``patch_test_globals`` /
    ``patch.object`` (session ``test_client``, routers/repository/observability
    fixtures). This guard is defense-in-depth: any unmanaged mutation of
    ``core.infra.database`` / ``core.app_lifespan`` globals is rolled back
    before the next test on this xdist worker starts. Root conftest runs
    outermost, so its teardown fires after every narrower fixture's own
    restore — the two always converge.
    """
    snapshot = capture_global_state()
    yield
    restore_global_state(snapshot)


@pytest.fixture(scope="session")
async def test_client() -> Any:
    """FastAPI TestClient backed by in-memory SQLite.

    Patches the database engine/session-factory singletons and the Redis
    dependency so the full FastAPI application runs without external
    infrastructure. Tables are created once per session; every patched
    global is restored on teardown.
    """
    # ── 1. Patch Redis BEFORE app import ────────────────────────────
    # Patch create_redis (the low-level connection factory) instead of
    # get_redis — some callers (login.py, password.py, register.py)
    # import get_redis via `from broker import get_redis` at
    # module level, creating local references that a later patch on
    # backend.broker.get_redis cannot override.  create_redis is always
    # looked up from its module at call time, so a single patch covers
    # every code path.
    from unittest.mock import AsyncMock, patch

    session_redis = AsyncMock()
    session_redis.incr.return_value = 1
    session_redis.expire.return_value = True
    session_redis.publish.return_value = 1

    patch_redis = patch("core.infra.redis_sentinel.create_redis", return_value=session_redis)
    patch_redis.start()

    # ── 2. Set up in-memory SQLite database ─────────────────────────
    # sqlite+aiosqlite:// defaults to StaticPool (one shared connection),
    # so tables created here stay visible for the whole session.
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        # ── 3. Rebind BOTH singletons to the session engine ─────────
        # Overwriting only _async_session_factory used to leave
        # get_async_engine() callers on a different, table-less in-memory
        # database (split-brain). Both globals must point at one engine,
        # and both must be restored when this fixture ends.
        with patch_test_globals(db={"_async_engine": engine, "_async_session_factory": factory}):
            # ── 4. Import the app and create ASGI client ────────────
            from core.app import app
            from httpx import ASGITransport, AsyncClient

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                try:
                    yield client
                finally:
                    patch_redis.stop()
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
async def db_engine(test_client: Any) -> None:
    """Companion fixture for tests that also request ``db_engine``.

    The actual database is already set up by ``test_client``; this fixture
    exists only to satisfy test signatures that request both.
    """
    return None


# ── Integration test skip helper ──────────────────────────────────────────────


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip @pytest.mark.integration tests when the backend is unreachable."""
    if item.get_closest_marker("integration") is None:
        return
    try:
        resp = httpx.get(f"{BASE}/api/models", timeout=3)
        if resp.status_code != 200:
            pytest.skip(f"Backend not available (status {resp.status_code})")
    except Exception:
        pytest.skip("Backend not available (connection failed)")


# ── Test data factories ──────────────────────────────────────────────────────
from tests.factories import (  # noqa: E402
    agent_factory,
    mcp_factory,
    prompt_factory,
    session_factory,
    skill_factory,
    team_factory,
    tool_factory,
)


@pytest.fixture
def agent_data():
    return agent_factory


@pytest.fixture
def team_data():
    return team_factory


@pytest.fixture
def session_data():
    return session_factory


@pytest.fixture
def tool_data():
    return tool_factory


@pytest.fixture
def prompt_data():
    return prompt_factory


@pytest.fixture
def skill_data():
    return skill_factory


@pytest.fixture
def mcp_data():
    return mcp_factory
