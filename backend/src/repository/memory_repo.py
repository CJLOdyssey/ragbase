"""Memory entry repository — CRUD for session-scoped agent memory entries."""

from datetime import UTC, datetime
from uuid import uuid4

from core.infra.database import MemoryEntry, get_session_factory
from sqlalchemy import select


async def get_session_memories(session_id: str) -> list[MemoryEntry]:
    """Return all memory entries for a session, ordered by creation time."""
    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(MemoryEntry)
            .where(MemoryEntry.session_id == session_id)
            .order_by(MemoryEntry.created_at)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def get_memory_entry(memory_id: str) -> MemoryEntry | None:
    """Fetch a single memory entry by ID, or None if missing."""
    factory = get_session_factory()
    async with factory() as session:
        return await session.get(MemoryEntry, memory_id)


async def create_memory_entry(
    session_id: str,
    run_id: str,
    agent_role: str,
    content_type: str,
    summary: str,
    details: str = "",
) -> MemoryEntry:
    """Persist a new agent memory entry.

    Args:
        session_id: The parent session UUID.
        run_id: The parent run UUID.
        agent_role: The agent role that produced this memory.
        content_type: Category label (e.g., "decision", "context").
        summary: Short summary of the memory.
        details: Optional detailed content.

    Returns:
        The newly created MemoryEntry instance.

    """
    factory = get_session_factory()
    async with factory() as session:
        obj = MemoryEntry(
            id=str(uuid4()),
            session_id=session_id,
            run_id=run_id,
            agent_role=agent_role,
            content_type=content_type,
            summary=summary,
            details=details,
            created_at=datetime.now(UTC),
        )
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj


async def clear_session_memories(session_id: str) -> None:
    """Delete all memory entries belonging to a session."""
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(MemoryEntry).where(MemoryEntry.session_id == session_id)
        result = await session.execute(stmt)
        for obj in result.scalars().all():
            await session.delete(obj)
        await session.commit()


async def delete_memory_entry(memory_id: str) -> bool:
    """Delete a single memory entry by ID. Returns False if not found."""
    factory = get_session_factory()
    async with factory() as session:
        obj = await session.get(MemoryEntry, memory_id)
        if not obj:
            return False
        await session.delete(obj)
        await session.commit()
        return True
