"""Repository test fixtures.

Provides an in-memory SQLite database for fast, isolated repository tests.
Monkey-patches ``backend.core.infra.database._async_session_factory`` so that
repository functions (which use ``get_session_factory()``) run against the
test database automatically.

Strategy:
  - Session-scoped engine (created once, reused across all tests).
  - Function-scoped autouse ``_setup_db`` drops + recreates ALL tables
    before each test so every test starts with a clean slate and the
    factory always points at the session engine.
"""


import pytest
from _global_state import patch_test_globals
from core.infra.database import Base
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)


@pytest.fixture(scope="session")
async def db_engine():
    """Create in-memory SQLite engine with all tables (session-scoped)."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture(autouse=True)
async def _setup_db(db_engine):
    """Point the global session factory at the test engine; restore on exit.

    Runs before EVERY test function — drops all tables, recreates them,
    and rebinds ``_async_session_factory`` to the session engine via the
    central snapshot/restore helper, so no mutation leaks past teardown.
    """
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    with patch_test_globals(db={"_async_session_factory": factory}):
        async with db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        yield
