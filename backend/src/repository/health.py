from __future__ import annotations

from core.infra.database import get_session_factory
from sqlalchemy import text


async def check_database() -> str:
    """Return 'ok' if a SELECT 1 succeeds, else the error message."""
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        return "ok"
    except Exception as e:
        return str(e)


async def check_redis() -> str:
    """Return 'ok' if Redis ping succeeds, else the error message."""
    try:
        from broker import get_redis

        r = get_redis()
        await r.ping()
        return "ok"
    except Exception as e:
        return str(e)
