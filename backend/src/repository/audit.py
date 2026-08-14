"""Audit repository — write audit log entries."""

from core.infra.database import get_session_factory
from orm import AuditLogDB


async def create_audit_entry(
    action: str,
    entity_type: str,
    entity_name: str = "",
    detail: str = "",
) -> None:
    """Append an entry to the audit log."""
    entry = AuditLogDB(
        action=action,
        entity_type=entity_type,
        entity_name=entity_name,
        detail=detail,
    )
    factory = get_session_factory()
    async with factory() as session:
        session.add(entry)
        await session.commit()
