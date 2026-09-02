"""Auth package — public API for JWT, RBAC, middleware, and password policy.

Consumers import named symbols (``from auth import get_user_id``); the
explicit ``__all__`` keeps the namespace free of submodule internals.
"""

from .auth import (
    AUTH_SECRET,
    PUBLIC_PATHS,
    PUBLIC_PREFIXES,
    AuthMiddleware,
    CurrentUser,
    create_token,
    decode_jwt,
    get_current_user,
    get_user_id,
    require_role,
)
from .password_policy import COMMON_PASSWORDS, PasswordPolicy, policy, validate_password

__all__ = [
    "AUTH_SECRET",
    "AuthMiddleware",
    "COMMON_PASSWORDS",
    "PUBLIC_PATHS",
    "PUBLIC_PREFIXES",
    "PasswordPolicy",
    "CurrentUser",
    "create_token",
    "decode_jwt",
    "get_current_user",
    "get_user_id",
    "policy",
    "require_role",
    "validate_password",
]
