"""Service layer — business-logic abstractions consumed by routers and tasks.

Business code imports directly from submodules (`from services.run_service import
run_service`). This package `__init__` deliberately does NOT re-bind the instance
names, so `from services import run_service` still yields the run_service *module*
(which exposes the `RUN_DISPATCH` module constant used by tests and pipelines).
"""

import services.run_service  # noqa: F401  (keeps the module importable via the package)
import services.session_service  # noqa: F401
from services.run_service import RunService
from services.session_service import with_requirement_message

__all__ = [
    "RunService",
    "with_requirement_message",
]
