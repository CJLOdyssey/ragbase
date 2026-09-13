"""Audit log helper — write audit entries for management CRUD operations.

Usage:
    from core.audit import log_audit
    await log_audit("create", "agent", "my-agent", "创建成功")

User / IP are captured automatically: the auth middleware calls
``set_audit_context`` on every request, so call sites don't need to pass
request context around.
"""

from contextvars import ContextVar

from repository.audit import create_audit_entry

_audit_ctx: ContextVar[dict[str, str] | None] = ContextVar("audit_ctx", default=None)


def set_audit_context(
    user_name: str = "",
    client_ip: str = "",
    user_agent: str = "",
    request_id: str = "",
) -> None:
    """Set the audit identity for the current request (called by auth middleware)."""
    _audit_ctx.set(
        {
            "user_name": user_name,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "request_id": request_id,
        }
    )


async def log_audit(
    action: str,
    entity_type: str,
    entity_name: str = "",
    detail: str = "",
) -> None:
    """Append an audit entry; user/IP default from the request-scoped context."""
    ctx = _audit_ctx.get() or {}
    await create_audit_entry(
        action=action,
        entity_type=entity_type,
        entity_name=entity_name,
        detail=detail,
        user_name=ctx.get("user_name", ""),
        client_ip=ctx.get("client_ip", ""),
        user_agent=ctx.get("user_agent", ""),
        request_id=ctx.get("request_id", ""),
    )
