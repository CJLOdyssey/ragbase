"""Checkpointer factory — creates the appropriate backend checkpointer.

Supported backends:
- ``memory``  — in-memory (no persistence, for tests / CI)
- ``sqlite``  — local SQLite file (default)
- ``postgres`` — PostgreSQL via ``langgraph-checkpoint-postgres``
"""

import os
from typing import Any

from core.infra.logging_config import get_logger
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

logger = get_logger(__name__)


def _resolve_backend(backend: str | None, dsn: str | None) -> tuple[str, str | None]:
    if backend is None:
        backend = os.environ.get("CHECKPOINTER_BACKEND", "sqlite")
    if dsn is None:
        dsn = os.environ.get("CHECKPOINTER_DSN")
    return backend, dsn


async def _create_checkpointer_async(backend: str, dsn: str | None) -> BaseCheckpointSaver[Any]:
    """Create the checkpointer based on backend configuration.

    Internal — shared async logic for both entry-points.
    """
    if backend == "postgres":
        if not dsn:
            raise ValueError("CHECKPOINTER_DSN is required for postgres backend")
        logger.info("Creating AsyncPostgresSaver checkpointer")
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        except ImportError as exc:
            raise ImportError(
                "Postgres checkpointer requires `langgraph-checkpoint-postgres` extra"
            ) from exc

        from psycopg import AsyncConnection
        from psycopg.rows import DictRow, dict_row

        conn = await AsyncConnection[DictRow].connect(
            dsn,
            autocommit=True,
            prepare_threshold=0,
            row_factory=dict_row,
        )
        saver = AsyncPostgresSaver(conn)
        await saver.setup()
        # Keep a reference to the underlying connection so close_checkpointer()
        # can release it — previously every run leaked a physical PG connection.
        setattr(saver, "_ckpt_conn", conn)  # noqa: B010 — dynamic attr on BaseCheckpointSaver
        return saver

    if backend == "sqlite":
        if not dsn:
            dsn = "checkpoints.db"
        logger.info("Creating AsyncSqliteSaver checkpointer (dsn=%s)", dsn)
        try:
            import aiosqlite
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        except ImportError as exc:
            raise ImportError(
                "SQLite checkpointer requires `langgraph-checkpoint-sqlite` extra "
                "and `aiosqlite` package"
            ) from exc

        aconn = await aiosqlite.connect(dsn)
        sqlite_saver = AsyncSqliteSaver(aconn)
        setattr(sqlite_saver, "_ckpt_conn", aconn)  # noqa: B010 — dynamic attr on BaseCheckpointSaver
        return sqlite_saver

    logger.info("Creating MemorySaver checkpointer (in-memory, no persistence)")
    return MemorySaver()


def create_checkpointer(
    backend: str | None = None,
    dsn: str | None = None,
) -> BaseCheckpointSaver[Any]:
    """Create a checkpointer (sync wrapper — suitable for CLI / tests).

    When called without arguments, reads ``CHECKPOINTER_BACKEND`` and
    ``CHECKPOINTER_DSN`` from environment. Defaults to SQLite.

    For async contexts (Celery worker, FastAPI lifespan) call
    ``create_checkpointer_async`` instead.
    """
    import asyncio
    import concurrent.futures

    backend, dsn = _resolve_backend(backend, dsn)
    logger.info("Creating checkpointer for backend=%s", backend)

    if backend == "memory":
        return MemorySaver()

    # If no loop is running we can safely call asyncio.run().
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_create_checkpointer_async(backend, dsn))

    # Already inside a running loop — run in a fresh loop on another thread.
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _pool:
        return _pool.submit(asyncio.run, _create_checkpointer_async(backend, dsn)).result()


async def create_checkpointer_async(
    backend: str | None = None,
    dsn: str | None = None,
) -> BaseCheckpointSaver[Any]:
    """Async checkpointer factory — safe to await inside a running loop.

    Preferred over ``create_checkpointer`` in Celery tasks and other async
    contexts because it avoids the overhead and edge-cases of crossing thread
    boundaries.
    """
    backend, dsn = _resolve_backend(backend, dsn)
    return await _create_checkpointer_async(backend, dsn)


async def close_checkpointer(saver: BaseCheckpointSaver[Any]) -> None:
    """Close the underlying connection of a checkpointer, if any.

    Pipelines create a fresh checkpointer per run (LangGraph graphs are
    compiled per run); without this the underlying psycopg/aiosqlite
    connection leaks. ``MemorySaver`` has no connection — no-op for it.
    """
    conn = getattr(saver, "_ckpt_conn", None)
    close = getattr(conn, "close", None) if conn is not None else None
    if close is None:
        return
    try:
        await close()
    except Exception:
        logger.debug("checkpointer close failed", exc_info=True)
