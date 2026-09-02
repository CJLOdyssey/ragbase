"""Core — shared infrastructure, config, models, and error handling.

Curated re-exports of the most commonly used public symbols for convenience.
Consumers may import from here or directly from the defining module
(e.g. ``from core import get_logger`` or ``from core.infra.logging_config import get_logger``).

``log_audit`` and ``seed_default_roles_and_admin`` are resolved lazily
(PEP 562): their defining modules sit above this package in the layering
(audit → repository, seed → orm), so importing them eagerly would make
``import orm`` re-enter a half-initialized ``core`` and fail with an
ImportError.
"""

from typing import Any

from ._interfaces import StreamResponseHandler
from .base import Base
from .config import LLMConfig, load_config
from .error_codes import ErrorCode, error_response
from .infra.events import EventBus, Events
from .infra.key_vault import (
    decrypt_api_key,
    encrypt_api_key,
)
from .infra.logging_config import get_logger
from .infra.metrics import metrics_endpoint
from .infra.request_logger import RequestLogMiddleware

__all__ = [
    "Base",
    "ErrorCode",
    "EventBus",
    "Events",
    "RequestLogMiddleware",
    "StreamResponseHandler",
    "LLMConfig",
    "decrypt_api_key",
    "encrypt_api_key",
    "error_response",
    "get_logger",
    "load_config",
    "log_audit",
    "metrics_endpoint",
    "seed_default_roles_and_admin",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "log_audit": ("core.audit", "log_audit"),
    "seed_default_roles_and_admin": ("core.seed", "seed_default_roles_and_admin"),
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    module_path, symbol = _LAZY_IMPORTS[name]
    return getattr(import_module(module_path), symbol)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
