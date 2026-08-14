"""Session repository — CRUD for conversation sessions."""

from datetime import UTC, datetime
from uuid import uuid4

from core.infra.database import SessionDB, get_session_factory
from core.infra.logging_config import get_logger
from sqlalchemy import desc, select, text

logger = get_logger(__name__)


async def create_session(
    title: str = "新对话", user_id: str = "default",
    kind: str = "normal",
) -> SessionDB:
    """Create a new conversation session and return the persisted row.

    Args:
        title: Display title for the session.
        user_id: Owner user ID.
        kind: Session kind — normal, agent, or team.

    Returns:
        The newly created SessionDB instance.

    """
    factory = get_session_factory()
    async with factory() as session:
        obj = SessionDB(
            id=str(uuid4()),
            title=title,
            user_id=user_id,
            kind=kind,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj


async def get_session(session_id: str) -> SessionDB | None:
    """Fetch a single session by its primary key ID."""
    factory = get_session_factory()
    async with factory() as session:
        return await session.get(SessionDB, session_id)


async def get_sessions(
    limit: int = 50, user_id: str | None = None
) -> list[SessionDB]:
    """Return recent sessions, optionally filtered by user.

    Args:
        limit: Maximum number of sessions to return.
        user_id: If set, only return sessions owned by this user.

    Returns:
        A list of SessionDB rows sorted by last-updated descending.

    """
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(SessionDB)
        if user_id:
            stmt = stmt.where(SessionDB.user_id == user_id)
        stmt = stmt.order_by(
            desc(SessionDB.is_pinned),
            desc(SessionDB.updated_at),
        ).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def update_session_pin(session_id: str, is_pinned: bool) -> SessionDB | None:
    """Pin/unpin a session. Returns the refreshed row, or None if not found."""
    factory = get_session_factory()
    async with factory() as session:
        obj = await session.get(SessionDB, session_id)
        if not obj:
            return None
        obj.is_pinned = is_pinned
        obj.updated_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(obj)
        return obj


async def update_session_title(session_id: str, title: str) -> SessionDB | None:
    """Update a session's title and return the refreshed row."""
    factory = get_session_factory()
    async with factory() as session:
        obj = await session.get(SessionDB, session_id)
        if not obj:
            return None
        obj.title = title
        obj.updated_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(obj)
        return obj


async def delete_session(session_id: str) -> bool:
    """Delete a session by ID. Returns False if not found."""
    factory = get_session_factory()
    async with factory() as session:
        obj = await session.get(SessionDB, session_id)
        if not obj:
            return False
        await session.delete(obj)
        await session.commit()
        return True


async def delete_vector_chunks_by_session(session_id: str) -> None:
    """Remove vector chunks orphaned by a session deletion (best-effort).

    Fail-open: a cleanup failure (e.g. vector_chunks absent in some
    environments) must never break the session deletion itself.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            await session.execute(
                text("DELETE FROM vector_chunks WHERE session_id = :sid"),
                {"sid": session_id},
            )
            await session.commit()
        except Exception:
            logger.warning(
                "Failed to clean vector chunks for session %s; orphans may remain",
                session_id,
                exc_info=True,
            )
