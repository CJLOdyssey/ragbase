"""User profile endpoints: config, me, merge guest data."""

from typing import Any

from auth import CurrentUser, get_current_user
from core.error_codes import ErrorCode, error_response
from core.infra.logging_config import get_logger
from fastapi import APIRouter, Depends, Request
from repository.auth import (
    get_user_by_email,
    get_user_by_id,
    get_user_roles,
)
from repository.auth import (
    merge_guest_data as _merge_guest_data,
)

from .schemas import AuthConfigResponse, MergeRequest, UserResponse

logger = get_logger(__name__)

router = APIRouter(tags=["auth"])


@router.get("/config", response_model=AuthConfigResponse)
def auth_config() -> Any:
    """Return the current auth mode and enabled status."""
    return AuthConfigResponse(enabled=True, mode="rbac")


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser = Depends(get_current_user)) -> Any:
    """Return the current authenticated user's profile."""
    user = await get_user_by_email(current_user.email)
    if user is None:
        user = await get_user_by_id(current_user.id)
    if user is None:
        raise error_response(ErrorCode.AUTH_USER_NOT_FOUND, detail="用户不存在")
    roles = await get_user_roles(user.id)
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        roles=roles,
        is_verified=user.is_verified,
    )


@router.post("/merge")
async def merge_guest_data(
    body: MergeRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """Merge ALL anonymous guest data into the authenticated user's account.

    Strategy: scan every row in the affected tables whose ``user_id``
    matches any of these patterns, then reassign it to the real user:
      1. The explicit ``guest_id`` sent by the frontend (browser's localStorage)
      2. The current ``X-User-ID`` header (may differ from #1, e.g. behind a proxy)
      3. The literal string ``anonymous`` (fallback in legacy clients)
      4. Any value starting with ``u_`` — the client-generated anonymous prefix
         (catches stale guest_ids from other browsers / localStorage resets)
    """
    x_user_id = request.headers.get("X-User-ID", "")
    explicit_ids = {body.guest_id, x_user_id, "anonymous"}
    explicit_ids.discard(current_user.id)
    explicit_ids.discard("")

    await _merge_guest_data(explicit_ids, current_user.id)

    logger.info(
        "Guest data merged: explicit=%s u_prefix=yes → user=%s",
        sorted(explicit_ids),
        current_user.id,
    )
    return {"status": "merged"}
