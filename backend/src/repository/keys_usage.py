"""API key usage accounting — token aggregation and audit logging."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.infra.database import KeyUsageLog, get_session_factory
from sqlalchemy import select


async def sum_user_tokens_since(user_id: str, since: datetime) -> int:
    """Total LLM tokens consumed by a user since a timestamp (budget check).

    Queries the append-only KeyUsageLog (tokens_total per call).
    """
    from sqlalchemy import func

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(func.coalesce(func.sum(KeyUsageLog.tokens_total), 0)).where(
                KeyUsageLog.user_id == user_id,
                KeyUsageLog.created_at >= since,
            )
        )
        return int(result.scalar_one())


async def log_key_usage(
    key_id: str | None,
    user_id: str,
    run_id: str | None,
    provider: str,
    model: str,
    tokens_prompt: int = 0,
    tokens_completion: int = 0,
    duration_ms: int = 0,
    status: str = "success",
    error_message: str | None = None,
) -> Any:
    """Record an LLM call in the audit log."""
    total = tokens_prompt + tokens_completion
    factory = get_session_factory()
    async with factory() as session:
        log = KeyUsageLog(
            id=str(uuid4()),
            key_id=key_id,
            user_id=user_id,
            run_id=run_id,
            provider=provider,
            model=model,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            tokens_total=total,
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
        )
        session.add(log)
        await session.commit()


async def get_key_usage_stats(user_id: str | None = None) -> dict[str, Any]:
    """Get usage statistics for API keys usage.

    If user_id is None or 'anonymous', returns stats across all users.
    """
    factory = get_session_factory()
    async with factory() as session:
        from sqlalchemy import func

        # Today's stats
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt_today = select(
            func.count(KeyUsageLog.id).label("requests"),
            func.sum(KeyUsageLog.tokens_total).label("tokens"),
        ).where(
            KeyUsageLog.created_at >= today_start,
            KeyUsageLog.status == "success",
        )
        if user_id and user_id != 'anonymous':
            stmt_today = stmt_today.where(KeyUsageLog.user_id == user_id)
        result_today = await session.execute(stmt_today)
        today = result_today.one()

        # Month's stats
        month_start = today_start.replace(day=1)
        stmt_month = select(
            func.count(KeyUsageLog.id).label("requests"),
            func.sum(KeyUsageLog.tokens_total).label("tokens"),
        ).where(
            KeyUsageLog.created_at >= month_start,
            KeyUsageLog.status == "success",
        )
        if user_id and user_id != 'anonymous':
            stmt_month = stmt_month.where(KeyUsageLog.user_id == user_id)
        result_month = await session.execute(stmt_month)
        month = result_month.one()

        return {
            "today_requests": today.requests or 0,
            "today_tokens": today.tokens or 0,
            "month_requests": month.requests or 0,
            "month_tokens": month.tokens or 0,
        }
