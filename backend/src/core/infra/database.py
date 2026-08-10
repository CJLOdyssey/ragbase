"""Database engine and session factory with slow-query detection."""

import os
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from core.base import Base
from core.infra.logging_config import get_logger
from sqlalchemy import (
    event,
    text,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

logger = get_logger(__name__)

# Queries exceeding this threshold (seconds) are logged as warnings
SLOW_QUERY_THRESHOLD = 0.5

# Load .env as fallback — never override already-set env vars (standard dotenv
# semantics). Prevents test fixtures (which set e.g. AUTH_MODE=legacy before
# core modules are imported) from being silently clobbered by backend/.env.
_env_file = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _, _value = _line.partition("=")
            _key = _key.strip()
            _value = _value.strip().strip('"').strip("'")
            if _key:
                os.environ.setdefault(_key, _value)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5433/ragbase",
)

_async_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None

def _attach_slow_query_listeners(engine: AsyncEngine) -> None:
    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def _before_execute(
        conn: Any, cursor: Any, statement: Any, parameters: Any, context: Any, executemany: Any
    ) -> None:
        conn.info.setdefault("_query_start", []).append(time.time())

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def _after_execute(conn: Any, cursor: Any, statement: Any, parameters: Any, context: Any, executemany: Any) -> None:
        start = conn.info["_query_start"].pop()
        elapsed = time.time() - start
        if elapsed > SLOW_QUERY_THRESHOLD:
            # Truncate long statements to avoid log flooding
            stmt = statement[:300] if isinstance(statement, str) else str(statement)[:300]
            logger.warning(
                "Slow query (%.2fs): %s",
                elapsed, stmt,
            )

def get_async_engine() -> AsyncEngine:
    """Return or create the singleton async SQLAlchemy engine."""
    global _async_engine
    if _async_engine is None:
        pool_size = int(os.environ.get("DATABASE_POOL_SIZE", "20"))
        max_overflow = int(os.environ.get("DATABASE_POOL_OVERFLOW", "10"))
        kwargs: dict[str, object] = dict(echo=False)
        if pool_size == 0:
            kwargs["poolclass"] = NullPool
        else:
            kwargs["poolclass"] = None
            kwargs["pool_size"] = pool_size
            kwargs["max_overflow"] = max_overflow
            kwargs["pool_pre_ping"] = True
            kwargs["pool_recycle"] = 3600
        _async_engine = create_async_engine(DATABASE_URL, **kwargs)
        _attach_slow_query_listeners(_async_engine)
    return _async_engine

def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return or create the singleton async session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(get_async_engine(), expire_on_commit=False)
    return _async_session_factory

async def init_db() -> None:
    """Bootstrap database tables on first run.

    Uses create_all() which is idempotent — only creates tables that don't
    already exist. For production deployments with existing data, use Alembic
    migrations instead:

        alembic upgrade head

    See alembic/versions/ for migration history.
    """
    # Lazy-register checkpoint model to avoid circular import
    from checkpoint import CheckpointDB  # noqa: F401

    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                """
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'sessions' AND column_name = 'kind'
                ) THEN
                    ALTER TABLE sessions ADD COLUMN kind VARCHAR(16) NOT NULL DEFAULT 'normal';
                END IF;
            END $$;
        """
            )
        )

    from core.seed import seed_default_roles_and_admin  # noqa: F401
    await seed_default_roles_and_admin()


async def get_session() -> AsyncIterator[AsyncSession]:
    """Async generator yielding a database session (FastAPI Depends)."""
    factory = get_session_factory()
    async with factory() as session:
        yield session

# ── Backward-compatible re-exports ─────────────────────────────────────
# All ORM models moved to backend.orm package.
# These imports keep `from core.infra.database import XxxDB` working.
from orm import (  # noqa: F401
    AssetDB,
    AttachmentDB,
    AuditLogDB,
    ChatMessage,
    CommandLogDB,
    FeedbackLog,
    KeyUsageLog,
    MemoryEntry,
    ProjectRun,
    PromptDB,
    RefreshTokenDB,
    RoleDB,
    SessionDB,
    UserApiKey,
    UserDB,
    UserRoleDB,
    VersionDB,
)

__all__ = [
    "AssetDB", "AttachmentDB", "AuditLogDB",
    "FeedbackLog",
    "ChatMessage", "CommandLogDB", "KeyUsageLog",
    "MemoryEntry", "ProjectRun",
    "PromptDB", "RefreshTokenDB",
    "RoleDB", "SessionDB",
    "UserApiKey",
    "UserDB", "UserRoleDB", "VersionDB",
]
