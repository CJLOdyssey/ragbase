"""Alembic environment config — async-aware with sync fallback for SQLite.

Dev (default): uses sync SQLite so ``alembic upgrade head`` works instantly.
Prod (postgres): set ``DATABASE_URL`` to a **sync** postgres URL (psycopg2) to
avoid async engine overhead:

    DATABASE_URL=postgresql+psycopg2://user:pass@host/db alembic upgrade head

If you must use asyncpg, switch to ``run_async()`` (see commented block below).
"""

import os
import re
from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context

from core.base import Base as ProjectBase

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Hook up our project's ORM metadata ──────────────────────────────────────
target_metadata = ProjectBase.metadata

# ── Resolve DB URL ───────────────────────────────────────────────────────────
# If the user set DATABASE_URL, honour it.
# Otherwise fall back to a sync-compatible SQLite URL (dev default).
raw_url = config.get_main_option("sqlalchemy.url", "")
env_url = os.environ.get("DATABASE_URL", "")

# If the ini template variable wasn't expanded, use env var or dev default
if "${" in raw_url:
    resolved_url = env_url or "sqlite:///./dev.db"
else:
    resolved_url = raw_url

# Strip async driver prefix so sync engine can handle it
_sync_url = re.sub(
    r"\+asyncpg$",
    "+psycopg2",
    re.sub(r"^postgresql\+asyncpg://", "postgresql+psycopg2://", resolved_url),
)


def run_migrations_offline() -> None:
    context.configure(
        url=resolved_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(_sync_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
