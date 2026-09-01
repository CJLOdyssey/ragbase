"""Version history API — generic version snapshot management.

No dependency on any business entity type (avoids Stamp Coupling).
Resource type and ID are passed as simple strings.

Ownership contract (QA A5-04): every ``resource_type`` must be registered
in ``KNOWN_RESOURCE_TYPES`` before the API accepts it. Types currently
registered are global-shared resources (prompt snapshots are visible and
editable by any authenticated user by design), so no per-user ownership
check applies yet. When a private entity type is added here, pair it with
an ownership resolver keyed by resource type — do NOT reopen untyped
read/write access.
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

# Snapshot-capable resource types. "prompt" is a global-shared resource;
# extend with an ownership resolver when private entities join.
KNOWN_RESOURCE_TYPES: frozenset[str] = frozenset({"prompt"})


class CreateVersionRequest(BaseModel):
    resource_type: str
    resource_id: str
    snapshot: dict[str, Any]


def _require_known_resource_type(resource_type: str) -> None:
    """Reject unregistered resource types instead of querying them blindly."""
    if resource_type not in KNOWN_RESOURCE_TYPES:
        raise error_response(
            ErrorCode.INVALID_REQUEST,
            detail=f"Unknown resource_type {resource_type!r}; "
            f"known types: {sorted(KNOWN_RESOURCE_TYPES)}",
        )


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


# Declared BEFORE the parametric route: FastAPI matches in declaration
# order, so otherwise ``detail`` gets captured as a resource_type below.
@router.get("/api/versions/{resource_type}/{resource_id}")
async def api_list_versions(
    resource_type: str,
    resource_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> Any:
    """List version history for a resource."""
    _require_known_resource_type(resource_type)
    return await list_versions(session, resource_type, resource_id, limit, offset)


@router.post("/api/versions", status_code=201)
async def api_create_version(
    req: CreateVersionRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Create a version snapshot for any resource type."""
    _require_known_resource_type(req.resource_type)
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
