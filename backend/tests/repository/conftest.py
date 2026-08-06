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

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from core.infra.database import (
    AgentConfigDB,
    Base,
)
from core.infra.database import (
    _async_session_factory as _real_factory,
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
    """Ensure the test session factory points at the test engine and tables exist.

    Runs before EVERY test function — drops all tables, recreates them,
    then sets ``_async_session_factory`` to the test engine. This prevents
    cross-test contamination when other fixtures monkey-patch the factory.
    """
    import core.infra.database as db

    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    db._async_session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    db._read_session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    yield
    # No teardown needed — next test's setup will drop everything anyway.


@pytest.fixture
async def sample_agent(db_engine):
    """Create and return a sample AgentConfigDB row for tests that need one."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        agent = AgentConfigDB(
            id=str(uuid.uuid4()),
            name="Sample Agent",
            role_identifier=f"sample_{uuid.uuid4().hex[:8]}",
            system_prompt="You are a sample agent.",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(agent)
        await session.commit()
        await session.refresh(agent)
        return agent
