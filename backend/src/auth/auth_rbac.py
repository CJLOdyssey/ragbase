"""RBAC user types, dependencies, and public-route configuration.

Provides ``CurrentUser``, ``get_current_user``, ``require_role``, ``get_user_id``,
and constants ``PUBLIC_PATHS`` / ``PUBLIC_PREFIXES``.
"""

from dataclasses import dataclass, field
from typing import Any

from core.infra.logging_config import get_logger
from fastapi import Depends, HTTPException, Request, status

from auth.auth_jwt import AUTH_SECRET, decode_jwt

logger = get_logger(__name__)


# ── RBAC Data Types ──────────────────────────────────────────────────────────


@dataclass
class CurrentUser:
    """Authenticated user context passed through FastAPI dependencies."""

    id: str = ""
    username: str = ""
    email: str = ""
    roles: list[str] = field(default_factory=list)


# ── RBAC Dependencies ────────────────────────────────────────────────────────


async def get_current_user(request: Request) -> CurrentUser:
    """FastAPI dependency — resolves the current user from JWT.

    Raises 401 when no valid JWT token is present.
    """
    # Try middleware-decoded user_id first (set by AuthMiddleware)
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        # AuthMiddleware skips /api/auth/* routes, so decode the JWT here.
        token = request.cookies.get("access_token")
        if not token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
        if token:
            payload = decode_jwt(token, AUTH_SECRET)
            if payload:
                user_id = payload.get("sub", "")

    if not user_id:
        logger.warning(
            "Auth missing token | client=%s",
            request.client.host if request.client else "?",
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供认证令牌")

    try:
        from repository.auth import get_user_by_id, get_user_roles

        user = await get_user_by_id(user_id)
        if user is not None:
            roles = await get_user_roles(user.id)
            logger.debug(
                "Auth user resolved | user=%s | roles=%s | client=%s",
                user.username, roles,
                request.client.host if request.client else "?",
            )
            return CurrentUser(
                id=user.id,
                username=user.username,
                email=user.email,
                roles=roles or ["member"],
            )
        logger.warning(
            "Auth user not found | user_id=%s", user_id,
        )
    except Exception:
        logger.warning("RBAC user lookup failed", exc_info=True)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或令牌无效")


def require_role(*names: str) -> Any:
    """Require the current user to have at least one of the named roles.

    Dependency factory — returns a 403 if none match.
    """

    def _role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:  # noqa: B008
        if not any(r in current_user.roles for r in names):
            logger.warning(
                "Auth role denied | user=%s | roles=%s | required=%s",
                current_user.username, current_user.roles, list(names),
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return current_user

    return _role_checker


# Routes exempt from authentication
PUBLIC_PATHS = {
    "/api/health",
    "/api/metrics",
    "/docs",
    "/openapi.json",
    "/redoc",
}
PUBLIC_PREFIXES = ("/ws/", "/api/auth/")


def get_user_id(request: Any) -> str:
    """Extract user identity from the authenticated request.

    Priority: auth middleware (request.state.user_id) → JWT cookie → 'anonymous'.
    """
    user_id: str | None = getattr(request.state, "user_id", None)
    if user_id:
        return user_id

    # JWT 有效但 sub 指向已删除/合并的用户（AuthMiddleware 已标记）
    if getattr(request.state, "user_invalid_token", False):
        return "anonymous"

    # Check httpOnly access_token cookie (set by login/register/verify/refresh endpoints)
    token = request.cookies.get("access_token")
    if token:
        payload = decode_jwt(token, AUTH_SECRET)
        if payload:
            uid = payload.get("sub")
            if isinstance(uid, str) and uid:
                return uid

    logger.warning("Unauthenticated ownership access | path=%s", request.url.path)
    return "anonymous"
