"""API keys repository — re-exports from keys_crud and keys_connectivity submodules."""

# Re-export all functions from split modules
from repository.keys_connectivity import (  # noqa: F401
    _test_connection_sync,
    test_api_key_connection,
)
from repository.keys_crud import (  # noqa: F401
    create_api_key,
    delete_api_key,
    get_api_key_for_model,
    get_api_key_for_use,
    get_api_keys,
    get_default_api_key,
    get_embedding_api_key,
    get_embedding_config,
    get_key_usage_stats,
    get_rerank_config,
    get_tool_api_key,
    log_key_usage,
    update_api_key,
)

__all__ = [
    "_test_connection_sync",
    "create_api_key",
    "delete_api_key",
    "get_api_key_for_model",
    "get_api_key_for_use",
    "get_api_keys",
    "get_default_api_key",
    "get_embedding_api_key",
    "get_embedding_config",
    "get_rerank_config",
    "get_key_usage_stats",
    "get_tool_api_key",
    "log_key_usage",
    "test_api_key_connection",
    "update_api_key",
]
