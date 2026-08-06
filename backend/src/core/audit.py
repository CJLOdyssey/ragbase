"""Audit log helper — write audit entries for management CRUD operations.

Extracted from database to eliminate three-layer violations
(routers were importing from database.py directly for log_audit).

Usage:
    from core.audit import log_audit
    await log_audit("create", "agent", "my-agent", "创建成功")
"""

from repository.audit import create_audit_entry


async def log_audit(
    action: str,
    entity_type: str,
    entity_name: str = "",
    detail: str = "",
) -> None:
    await create_audit_entry(
        action=action,
        entity_type=entity_type,
        entity_name=entity_name,
        detail=detail,
    )
