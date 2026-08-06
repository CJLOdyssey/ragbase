"""Command log repository — insert execution audit records."""

from uuid import uuid4

from core.infra.database import CommandLogDB, get_session_factory


async def log_command(
    session_id: str,
    command_id: str,
    command_name: str,
    payload: str,
    result: str,
) -> None:
    """Insert a command execution log entry."""
    factory = get_session_factory()
    async with factory() as db:
        log = CommandLogDB(
            id=str(uuid4()),
            session_id=session_id,
            command_id=command_id,
            command_name=command_name,
            payload=payload,
            result=result,
        )
        db.add(log)
        await db.commit()
