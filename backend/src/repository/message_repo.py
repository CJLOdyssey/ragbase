"""Chat message repository — persistence for conversation messages."""

from datetime import UTC, datetime
from uuid import uuid4

from core.infra.database import ChatMessage, ProjectRun, get_session_factory
from sqlalchemy import select


async def save_message(run_id: str, role: str, agent_name: str, content: str, round_number: int, thinking: str | None = None) -> None:  # noqa: E501
    """Persist a chat message to the database."""
    msg = ChatMessage(
        id=str(uuid4()),
        run_id=run_id,
        role=role,
        agent_name=agent_name,
        content=content,
        thinking=thinking,
        round_number=round_number,
        created_at=datetime.now(UTC),
    )
    factory = get_session_factory()
    async with factory() as session:
        session.add(msg)
        await session.commit()


async def update_message_content(message_id: str, content: str) -> None:
    """Replace a chat message's content in place."""
    factory = get_session_factory()
    async with factory() as session:
        msg = await session.get(ChatMessage, message_id)
        if msg is not None:
            msg.content = content
            await session.commit()


async def get_messages(run_id: str) -> list[ChatMessage]:
    """Return all chat messages for a run, ordered chronologically."""
    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(ChatMessage).where(ChatMessage.run_id == run_id).order_by(ChatMessage.created_at)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def get_run_messages(run_id: str) -> list[ChatMessage]:
    """Return all chat messages for a run, ordered chronologically (alias)."""
    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(ChatMessage).where(ChatMessage.run_id == run_id).order_by(ChatMessage.created_at)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def get_session_messages(
    session_id: str, exclude_run_id: str | None = None
) -> list[ChatMessage]:
    """Return all chat messages across all runs in a session, ordered chronologically.

    Args:
        session_id: The parent session UUID.
        exclude_run_id: If provided, skip messages from this run.

    Returns:
        A list of ChatMessage rows sorted by creation time.

    """
    factory = get_session_factory()
    async with factory() as session:
        # Get all run IDs for this session
        runs_stmt = select(ProjectRun.id).where(ProjectRun.session_id == session_id)
        if exclude_run_id:
            runs_stmt = runs_stmt.where(ProjectRun.id != exclude_run_id)
        runs_result = await session.execute(runs_stmt)
        run_ids = [r[0] for r in runs_result.all()]

        if not run_ids:
            return []

        # Get all messages for these runs
        msgs_stmt = (
            select(ChatMessage)
            .where(ChatMessage.run_id.in_(run_ids))
            .order_by(ChatMessage.created_at)
        )
        msgs_result = await session.execute(msgs_stmt)
        return list(msgs_result.scalars().all())
