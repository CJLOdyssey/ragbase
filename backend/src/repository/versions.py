"""Version repository — manages version snapshots for business entities.

Follows Functional Cohesion: all methods serve the single purpose of
managing version snapshots. No knowledge of business entity types.

Usage::

    from repository.versions import create_version, list_versions

    v = await create_version(session, "prompt", prompt_id, {"content": "..."}, "user-1")
    history = await list_versions(session, "prompt", prompt_id)  # newest first
"""

from typing import Any
from uuid import uuid4

from core.infra.database import VersionDB
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# Distinct writers (multi-instance) may compute the same max+1 concurrently;
# the ux_versions_resource_version unique index turns the race into an
# IntegrityError. A handful of retries is ample: the window is one flush.
_MAX_NUMBERING_RETRIES = 3


async def create_version(
    session: AsyncSession,
    resource_type: str,
    resource_id: str,
    snapshot: dict[str, Any],
    created_by: str | None = None,
) -> dict[str, Any]:
    """Create a new version snapshot. Returns the created version dict.

    Version numbers are computed as ``max(version_num) + 1`` and guarded by
    a unique index; on a concurrent-writer conflict the insert is retried
    inside a SAVEPOINT so the caller's outer transaction stays intact.
    """
    attempt = 0
    while True:
        attempt += 1
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

        v = VersionDB(
            id=str(uuid4()),
            resource_type=resource_type,
            resource_id=resource_id,
            version_num=last_num + 1,
            snapshot=snapshot,
            created_by=created_by,
        )
        try:
            async with session.begin_nested():
                session.add(v)
                await session.flush()
        except IntegrityError:
            if attempt >= _MAX_NUMBERING_RETRIES:
                raise
            # Another writer took this number between our SELECT and INSERT;
            # the savepoint rollback already discarded the unpersisted row —
            # loop back and recompute max(version_num).
            continue
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
