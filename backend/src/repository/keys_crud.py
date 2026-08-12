"""API key repository — facade over keys_crud_core / keys_resolve / keys_usage.

Splitting kept the public import surface unchanged; all callers keep importing
from ``repository.keys_crud``.
"""

from repository.keys_crud_core import (
    create_api_key,
    delete_api_key,
    get_api_key_for_use,
    get_api_keys,
    update_api_key,
)
from repository.keys_resolve import (
    get_api_key_for_model,
    get_default_api_key,
    get_embedding_api_key,
    get_embedding_config,
    get_rerank_config,
    get_tool_api_key,
)
from repository.keys_usage import (
    get_key_usage_stats,
    log_key_usage,
    sum_user_tokens_since,
)

__all__ = [
    "create_api_key",
    "get_api_keys",
    "get_api_key_for_use",
    "update_api_key",
    "delete_api_key",
    "get_api_key_for_model",
    "get_default_api_key",
    "get_rerank_config",
    "get_embedding_config",
    "get_embedding_api_key",
    "get_tool_api_key",
    "sum_user_tokens_since",
    "log_key_usage",
    "get_key_usage_stats",
]
