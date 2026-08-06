"""Unified snapshot helper — manages version snapshot session lifecycle.

Usage::

    from repository.snapshot_helper import build_table_snapshot

    snapshot = build_table_snapshot(item)
"""

from collections.abc import Callable
from typing import Any

from core.infra.logging_config import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


async def with_session(
    fn: Callable[..., Any],
    *,
    resource_type: str,
    resource_id: str,
    session: AsyncSession | None = None,
    **kwargs: Any,
) -> None:
    """Execute *fn* inside a session, or reuse an existing one.

    If ``session`` is provided, *fn* is called directly with it.
    Otherwise a new session is obtained from the factory, *fn* is
    run inside it, and the session is committed.

    Args:
        fn: Async callable that takes ``(session, resource_id)``.
        resource_type: Version resource type label (e.g. ``"run"``).
        resource_id: The business-entity primary key.
        session: An optional existing async session to reuse.
        **kwargs: Forwarded to *fn*.
    """
    if session is not None:
        await fn(session, resource_type, resource_id, **kwargs)
        return

    from core.infra.database import get_session_factory

    factory = get_session_factory()
    async with factory() as s:
        await fn(s, resource_type, resource_id, **kwargs)
        await s.commit()


def build_table_snapshot(item: Any, exclude: set[str] | None = None) -> dict[str, Any]:
    """Build a snapshot dict from an SQLAlchemy model instance by iterating
    its table columns.

    Args:
        item: An SQLAlchemy model instance with ``__table__``.
        exclude: Column names to exclude (``{"id", "created_at", "updated_at"}``
                 by default).

    Returns:
        A JSON-safe ``dict`` suitable for ``create_version``.
    """
    if exclude is None:
        exclude = {"id", "created_at", "updated_at"}
    snapshot: dict[str, Any] = {}
    for c in item.__table__.columns:
        name = c.name
        if name in exclude:
            continue
        val = getattr(item, name, None)
        if val is not None and hasattr(val, "isoformat"):
            val = val.isoformat()
        snapshot[name] = val
    return snapshot
