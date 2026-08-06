"""Checkpoint repository — CRUD operations for agent checkpoints.

Separated from the factory layer so it can evolve independently.
"""

from uuid import uuid4

from core.infra.database import get_session_factory
from core.infra.logging_config import get_logger

from checkpoint.models import AgentCheckpoint, CheckpointDB

logger = get_logger(__name__)


async def save_checkpoint(checkpoint: AgentCheckpoint) -> str:
    """Persist an agent checkpoint to the database. Returns checkpoint ID."""
    factory = get_session_factory()
    async with factory() as session:
        obj = CheckpointDB(
            id=str(uuid4()),
            session_id=checkpoint.session_id,
            run_id=checkpoint.run_id,
            step_index=checkpoint.step_index,
            agent_state=checkpoint.to_json(),
        )
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj.id


async def load_latest_checkpoint(session_id: str) -> AgentCheckpoint | None:
    """Load the most recent checkpoint for a session."""
    factory = get_session_factory()
    async with factory() as session:
        from sqlalchemy import desc, select

        stmt = (
            select(CheckpointDB)
            .where(CheckpointDB.session_id == session_id)
            .order_by(desc(CheckpointDB.created_at))
            .limit(1)
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return AgentCheckpoint.from_json(row.agent_state)


async def list_checkpoints(session_id: str) -> list[AgentCheckpoint]:
    """List all checkpoints for a session, oldest first."""
    factory = get_session_factory()
    async with factory() as session:
        from sqlalchemy import select

        stmt = (
            select(CheckpointDB)
            .where(CheckpointDB.session_id == session_id)
            .order_by(CheckpointDB.created_at)
        )
        result = await session.execute(stmt)
        return [AgentCheckpoint.from_json(row.agent_state) for row in result.scalars()]
