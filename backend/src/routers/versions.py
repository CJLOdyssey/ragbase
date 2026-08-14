"""Version history API — generic version snapshot management.

No dependency on any business entity type (avoids Stamp Coupling).
Resource type and ID are passed as simple strings.
"""

from typing import Any

from auth import get_user_id
from core.error_codes import ErrorCode, error_response
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from repository.deps import get_session
from repository.versions import (
    create_version,
    get_version,
    list_versions,
)
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["versions"])


class CreateVersionRequest(BaseModel):
    resource_type: str
    resource_id: str
    snapshot: dict[str, Any]


@router.get("/api/versions/{resource_type}/{resource_id}")
async def api_list_versions(
    resource_type: str,
    resource_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> Any:
    """List version history for a resource."""
    return await list_versions(session, resource_type, resource_id, limit, offset)


@router.get("/api/versions/detail/{version_id}")
async def api_get_version(
    version_id: str,
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Get a single version by ID."""
    v = await get_version(session, version_id)
    if not v:
        raise error_response(ErrorCode.VERSION_NOT_FOUND, detail="Version not found")
    return v


@router.post("/api/versions", status_code=201)
async def api_create_version(
    req: CreateVersionRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Create a version snapshot for any resource type."""
    user_id = get_user_id(request)
    result = await create_version(
        session,
        req.resource_type,
        req.resource_id,
        req.snapshot,
        user_id,
    )
    # The Depends(get_session) dependency closes the session on exit, which
    # rolls back uncommitted changes — commit here or the snapshot silently
    # never persists (API returns 201 but writes nothing).
    await session.commit()
    return result
