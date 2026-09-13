"""Audit repository — write audit log entries."""

from core.infra.database import get_session_factory
from orm import AuditLogDB


async def create_audit_entry(
    action: str,
    entity_type: str,
    entity_name: str = "",
    detail: str = "",
    user_name: str = "",
    client_ip: str = "",
    user_agent: str = "",
    request_id: str = "",
) -> None:
    """Append an entry to the audit log.

    Usage::

        await create_audit_entry("user.delete", "user", entity_name=user_id)

    The context fields (user/IP/agent/request id) are normally filled by
    ``core.audit.log_audit`` from the request-scoped audit context.
    """
    entry = AuditLogDB(
        action=action,
        entity_type=entity_type,
        entity_name=entity_name,
        detail=detail,
        user_name=user_name,
        client_ip=client_ip,
        user_agent=user_agent,
        request_id=request_id,
    )
    factory = get_session_factory()
    async with factory() as session:
        session.add(entry)
        await session.commit()
