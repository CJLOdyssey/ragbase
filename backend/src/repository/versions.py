"""Version repository — manages version snapshots for business entities.

Follows Functional Cohesion: all methods serve the single purpose of
managing version snapshots. No knowledge of business entity types.
"""

from typing import Any
from uuid import uuid4

from core.infra.database import VersionDB
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def create_version(
    session: AsyncSession,
    resource_type: str,
    resource_id: str,
    snapshot: dict[str, Any],
    created_by: str | None = None,
) -> dict[str, Any]:
    """Create a new version snapshot. Returns the created version dict."""
    result = await session.execute(
        select(VersionDB.version_num)
        .where(
            VersionDB.resource_type == resource_type,
            VersionDB.resource_id == resource_id,
        )
        .order_by(VersionDB.version_num.desc())
        .limit(1)
    )
    last_num = result.scalar_one_or_none() or 0
    version_num = last_num + 1

    v = VersionDB(
        id=str(uuid4()),
        resource_type=resource_type,
        resource_id=resource_id,
        version_num=version_num,
        snapshot=snapshot,
        created_by=created_by,
    )
    session.add(v)
    await session.flush()

    return {
        "id": v.id,
        "resource_type": v.resource_type,
        "resource_id": v.resource_id,
        "version_num": v.version_num,
        "snapshot": v.snapshot,
        "created_by": v.created_by,
        "created_at": v.created_at.isoformat(),
    }


async def list_versions(
    session: AsyncSession,
    resource_type: str,
    resource_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List versions for a resource, newest first."""
    result = await session.execute(
        select(VersionDB)
        .where(
            VersionDB.resource_type == resource_type,
            VersionDB.resource_id == resource_id,
        )
        .order_by(VersionDB.version_num.desc())
        .offset(offset)
        .limit(limit)
    )
    return [
        {
            "id": v.id,
            "version_num": v.version_num,
            "snapshot": v.snapshot,
            "created_by": v.created_by,
            "created_at": v.created_at.isoformat(),
        }
        for v in result.scalars().all()
    ]


async def get_version(session: AsyncSession, version_id: str) -> dict[str, Any] | None:
    """Get a single version by ID."""
    result = await session.execute(
        select(VersionDB).where(VersionDB.id == version_id)
    )
    v = result.scalar_one_or_none()
    if not v:
        return None
    return {
        "id": v.id,
        "resource_type": v.resource_type,
        "resource_id": v.resource_id,
        "version_num": v.version_num,
        "snapshot": v.snapshot,
        "created_by": v.created_by,
        "created_at": v.created_at.isoformat(),
    }


async def count_versions(resource_type: str, resource_id: str) -> int:
    """Count version snapshots for a resource."""
    from core.infra.database import VersionDB, get_session_factory
    from sqlalchemy import func, select

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(func.count(VersionDB.id)).where(
                VersionDB.resource_type == resource_type,
                VersionDB.resource_id == resource_id,
            )
        )
        return int(result.scalar_one() or 0)
