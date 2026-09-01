"""API keys repository — re-exports from keys_crud and keys_connectivity submodules.

Usage::

    from repository.keys import create_api_key, get_api_keys, fetch_models_for_provider

    keys = await get_api_keys(user_id)  # masked, never plaintext
    result = await fetch_models_for_provider(provider, api_key, base_url)
"""

from repository.keys_connectivity import (  # noqa: F401
    fetch_models_for_provider,
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
    "create_api_key",
    "delete_api_key",
    "fetch_models_for_provider",
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
