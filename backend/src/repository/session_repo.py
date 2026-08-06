"""Session repository — CRUD for conversation sessions."""

from datetime import UTC, datetime
from uuid import uuid4

from core.infra.database import SessionDB, get_session_factory
from sqlalchemy import desc, select


async def create_session(
    title: str = "新对话", user_id: str = "default", agent_id: str | None = None,
    kind: str = "normal",
) -> SessionDB:
    """Create a new conversation session and return the persisted row.

    Args:
        title: Display title for the session.
        user_id: Owner user ID.
        agent_id: Optional bound agent config ID.
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
            agent_id=agent_id,
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
    limit: int = 50, user_id: str | None = None, agent_id: str | None = None
) -> list[SessionDB]:
    """Return recent sessions, optionally filtered by user or agent.

    Args:
        limit: Maximum number of sessions to return.
        user_id: If set, only return sessions owned by this user.
        agent_id: If set, only return sessions bound to this agent config.

    Returns:
        A list of SessionDB rows sorted by last-updated descending.

    """
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(SessionDB).order_by(desc(SessionDB.updated_at)).limit(limit)
        if agent_id:
            stmt = stmt.where(SessionDB.agent_id == agent_id)
        if user_id:
            stmt = stmt.where(SessionDB.user_id == user_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())


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
