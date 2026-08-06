"""Core — shared infrastructure, config, models, and error handling.

Public symbols are explicitly imported below so callers can use either:
    from core import XXX
    from core.xxx import XXX
"""

from ._interfaces import StreamResponseHandler, ToolDescriptor, ToolExecutor
from .audit import log_audit
from .base import Base
from .config import TeamConfig, load_config
from .error_codes import ErrorCode, error_response
from .infra.events import EventBus, Events
from .infra.key_vault import (
    decrypt_api_key,
    encrypt_api_key,
)
from .infra.logging_config import get_logger
from .infra.metrics import metrics_endpoint
from .infra.request_logger import RequestLogMiddleware
from .seed import seed_default_roles_and_admin

__all__ = [
    "Base",
    "ErrorCode",
    "EventBus",
    "Events",
    "RequestLogMiddleware",
    "StreamResponseHandler",
    "TeamConfig",
    "ToolDescriptor",
    "ToolExecutor",
    "decrypt_api_key",
    "encrypt_api_key",
    "error_response",
    "get_logger",
    "load_config",
    "log_audit",
    "metrics_endpoint",
    "seed_default_roles_and_admin",
]
