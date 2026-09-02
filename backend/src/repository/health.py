"""Health-check probes for the /api/health endpoint.

Each probe returns ``"ok"`` or the failure message — never raises, so a
single broken dependency reports its own error without taking the whole
health endpoint down.

Usage::

    from repository.health import check_database, check_redis

    status = await check_database()  # "ok" | error message
"""

from __future__ import annotations

from broker import get_redis
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
        r = get_redis()
        await r.ping()
        return "ok"
    except Exception as e:
        return str(e)
