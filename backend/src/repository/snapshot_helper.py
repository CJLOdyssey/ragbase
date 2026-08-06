"""Unified snapshot helper — manages version snapshot session lifecycle.

Replaces the duplicated ``_snapshot_*`` / ``_do_snapshot_*`` pattern
that previously lived in 6 router files (agents, teams, mcps, skills,
prompts, tools). Each of those files had an identical session-management
boilerplate with a lazy ``from core.infra.database import get_session_factory``
that violated the three-layer strictness rule.

Usage::

    from repository.snapshot_helper import create_snapshot

    # Called from a router (session created internally)
    await create_snapshot("agent", agent_id, snapshot_data, "system")

    # Called from a repository function that already has a session
    await create_snapshot("agent", agent_id, snapshot_data, "system", session=existing_session)
"""

from collections.abc import Callable
from typing import Any

from core.infra.logging_config import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

from repository.versions import create_version

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
        resource_type: Version resource type label (e.g. ``"agent"``).
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


async def create_snapshot_from_dict(
    resource_type: str,
    resource_id: str,
    snapshot: dict[str, Any],
    created_by: str = "system",
    session: AsyncSession | None = None,
) -> None:
    """Create a version snapshot from a pre-built dictionary.

    This is the simplest variant — callers prepare the snapshot dict
    themselves.

    Args:
        resource_type: ``"agent"``, ``"team"``, ``"prompt"``, etc.
        resource_id: Business-entity primary key.
        snapshot: Arbitrary key-value snapshot to persist.
        created_by: Who created the snapshot (default ``"system"``).
        session: Optional existing async session.
    """

    async def _save(s: Any, rt: str, rid: str, **kw: Any) -> None:
        await create_version(s, rt, rid, kw["snapshot"], kw.get("created_by", "system"))

    await with_session(
        _save,
        resource_type=resource_type,
        resource_id=resource_id,
        session=session,
        snapshot=snapshot,
        created_by=created_by,
    )


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
