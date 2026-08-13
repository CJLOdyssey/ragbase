"""RBAC user types, dependencies, and public-route configuration.

Provides ``CurrentUser``, ``get_current_user``, ``require_role``, ``get_user_id``,
and constants ``PUBLIC_PATHS`` / ``PUBLIC_PREFIXES``.
"""

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from fastapi import Depends, HTTPException, Request, status

if TYPE_CHECKING:
    # Only for type checker — runtime uses deferred imports to avoid circular dep
    from orm.auth import RoleDB, UserDB, UserRoleDB

from core.infra.logging_config import get_logger

from auth.auth_jwt import AUTH_SECRET, decode_jwt

logger = get_logger(__name__)

AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "0") == "1"
AUTH_MODE = os.environ.get("AUTH_MODE", "legacy")

# Login wall: when enabled, unauthenticated business API requests are rejected
# with 401 instead of passing through as the "anonymous" guest namespace.
# Default off — guest access is the product default; set to 1 for public
# deployments that require sign-in before use.
AUTH_REQUIRE_LOGIN = os.environ.get("AUTH_REQUIRE_LOGIN", "0") == "1"

# Validate AUTH_SECRET at import time for RBAC mode
if AUTH_MODE == "rbac" and AUTH_ENABLED and AUTH_SECRET == "":
    raise RuntimeError(
        "AUTH_MODE=rbac and AUTH_ENABLED=1 requires AUTH_SECRET to be set "
        "(minimum 32 characters). Set it via environment variable."
    )
if AUTH_MODE == "rbac" and AUTH_ENABLED and len(AUTH_SECRET) < 32:
    raise RuntimeError(
        "AUTH_SECRET must be at least 32 characters for RBAC mode. "
        f"Current length: {len(AUTH_SECRET)}"
    )


# ── RBAC Data Types ──────────────────────────────────────────────────────────


@dataclass
class CurrentUser:
    """Authenticated user context passed through FastAPI dependencies."""

    id: str = "admin"
    username: str = "admin"
    email: str = "admin@example.com"
    roles: list[str] = field(default_factory=lambda: ["admin"])


# ── RBAC Dependencies ────────────────────────────────────────────────────────


async def get_current_user(request: Request) -> CurrentUser:
    """FastAPI dependency — resolves the current user.

    In ``legacy`` mode returns a fixed admin user without any DB query.
    In ``rbac`` mode uses the JWT-decoded user_id (from middleware or self-decoded).
    Raises 401 when no valid JWT token is present.
    """
    # Read at call time, not import time: test fixtures set AUTH_MODE before
    # requests but after this module may already be imported.
    if os.environ.get("AUTH_MODE", "legacy") == "legacy":
        return CurrentUser()

    # Try middleware-decoded user_id first (set by AuthMiddleware for non-auth routes)
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        # AuthMiddleware skips /api/auth/* routes, so decode the JWT here.
        # Priority: Authorization Bearer header (legacy) → access_token httpOnly cookie.
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            payload = decode_jwt(auth_header[7:], AUTH_SECRET)
            if payload:
                user_id = payload.get("sub", "")
    if not user_id:
        # Fallback to httpOnly cookie (set by login/register/verify/refresh endpoints)
        token = request.cookies.get("access_token")
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
            logger.info(
                "Auth login success | user=%s | roles=%s | client=%s",
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

    Usage::

        @router.post("/agents")
        async def create(
            req: AgentCreateRequest,
            user: CurrentUser = Depends(require_role("admin", "manager")),
        ): ...
    """

    def _role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:  # noqa: B008
        if os.environ.get("AUTH_MODE", "legacy") == "legacy":
            return current_user
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
    The ``X-User-ID`` header is ONLY trusted in legacy/guest mode (auth disabled),
    where it is a guest-data namespace, NOT a security boundary. When auth is
    enabled, unauthenticated requests resolve to ``anonymous``.
    """
    user_id: str | None = getattr(request.state, "user_id", None)
    if user_id:
        return user_id

    # JWT 有效但 sub 指向已删除/合并的用户（AuthMiddleware 已标记）——
    # 不信任该身份，回退 anonymous，避免误导性 400（key/附件按 user 归属）。
    if getattr(request.state, "user_invalid_token", False) and AUTH_ENABLED:
        return "anonymous"

    # Check httpOnly access_token cookie (set by login/register/verify/refresh endpoints)
    token = request.cookies.get("access_token")
    if token:
        payload = decode_jwt(token, AUTH_SECRET)
        if payload:
            uid = payload.get("sub")
            if isinstance(uid, str) and uid:
                return uid

    if AUTH_ENABLED:
        logger.warning("Unauthenticated ownership access | path=%s", request.url.path)
        return "anonymous"

    return str(request.headers.get("X-User-ID", "anonymous"))
