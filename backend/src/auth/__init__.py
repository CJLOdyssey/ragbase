def __getattr__(name: str) -> object:
    if name == "AUTH_SECRET":
        from .auth_jwt import AUTH_SECRET
        return AUTH_SECRET
    raise AttributeError(f"module 'backend.auth' has no attribute {name!r}")

from .auth import *  # noqa: F403
from .auth_jwt import *  # noqa: F403
from .auth_middleware import *  # noqa: F403
from .auth_rbac import *  # noqa: F403
from .password_policy import *  # noqa: F403

__all__ = [x for x in dir() if not x.startswith("_")]
