"""Auth re-export hub.

Aggregates the public API from JWT primitives, RBAC dependencies, and
middleware so ``from auth import X`` keeps working. ``__all__`` defines the
single source of truth for what the auth package exposes.
"""

from auth.auth_jwt import AUTH_SECRET, create_token, decode_jwt
from auth.auth_middleware import AuthMiddleware
from auth.auth_rbac import (
    PUBLIC_PATHS,
    PUBLIC_PREFIXES,
    CurrentUser,
    get_current_user,
    get_user_id,
    require_role,
)

__all__ = [
    "AUTH_SECRET",
    "AuthMiddleware",
    "PUBLIC_PATHS",
    "PUBLIC_PREFIXES",
    "CurrentUser",
    "create_token",
    "decode_jwt",
    "get_current_user",
    "get_user_id",
    "require_role",
]
