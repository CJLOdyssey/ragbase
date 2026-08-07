"""Repository layer — async data-access functions and CRUD helpers.
Explicit imports from each submodule — no star-imports."""

# ruff: noqa: I001 — isort wants alphabetical, we group by module

from repository.assets import (
    create_asset,
    delete_asset,
    get_asset,
    get_asset_for_user,
    increment_asset_usage,
    list_assets_by_user,
    set_asset_indexed,
)

from repository.attachments import (
    create_attachment,
    delete_attachment,
    get_attachment_by_id,
    list_attachments_by_run,
    list_attachments_by_session,
)

from repository.health import check_database, check_redis

from repository.audit import create_audit_entry

from repository.auth import (
    consume_refresh_token,
    create_refresh_token,
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    get_user_roles,
    increment_failed_logins,
    mark_user_verified,
    merge_guest_data,
    reset_failed_logins,
    revoke_all_user_tokens,
    revoke_token_family,
    update_password,
)

from repository.command_logs import log_command

from repository.core import apply_owner_filter

from repository.keys import (
    create_api_key,
    delete_api_key,
    get_api_key_for_model,
    get_api_key_for_use,
    get_api_keys,
    get_default_api_key,
    get_embedding_api_key,
    get_key_usage_stats,
    get_tool_api_key,
    log_key_usage,
    test_api_key_connection,
    update_api_key,
)

from repository.memory_repo import (
    clear_session_memories,
    create_memory_entry,
    delete_memory_entry,
    get_session_memories,
)

from repository.message_repo import (
    get_messages,
    get_run_messages,
    get_session_messages,
    save_message,
    update_message_content,
    update_message_versions,
)

from repository.prompts import (
    create_prompt,
    delete_prompt,
    get_prompt,
    get_prompts,
    get_prompts_as_dicts,
    update_prompt,
)

from repository.run_repo import (
    create_run,
    get_run,
    get_run_for_user,
    get_runs,
    get_runs_by_session_ids,
    get_session_runs,
    update_run_result,
    update_run_status,
)

from repository.session_repo import (
    create_session,
    delete_session,
    get_session,
    get_sessions,
    update_session_title,
)

from repository.versions import (
    count_versions,
    create_version,
    get_version,
    list_versions,
)

__all__ = [
    "apply_owner_filter",
    "check_database",
    "check_redis",
    "clear_session_memories",
    "consume_refresh_token",
    "create_api_key",
    "create_asset",
    "create_attachment",
    "create_audit_entry",
    "create_memory_entry",
    "create_prompt",
    "create_refresh_token",
    "create_run",
    "create_session",
    "create_user",
    "count_versions",
    "create_version",
    "delete_api_key",
    "delete_asset",
    "delete_attachment",
    "delete_memory_entry",
    "delete_prompt",
    "delete_session",
    "get_api_key_for_model",
    "get_api_key_for_use",
    "get_api_keys",
    "get_asset",
    "get_asset_for_user",
    "get_attachment_by_id",
    "get_default_api_key",
    "get_embedding_api_key",
    "get_key_usage_stats",
    "get_messages",
    "get_prompt",
    "get_prompts",
    "get_prompts_as_dicts",
    "get_run",
    "get_run_for_user",
    "get_run_messages",
    "get_runs",
    "get_runs_by_session_ids",
    "get_session",
    "get_session_memories",
    "get_session_messages",
    "get_session_runs",
    "get_sessions",
    "get_template",
    "get_tool_api_key",
    "get_user_by_email",
    "get_user_by_id",
    "get_user_by_username",
    "get_user_roles",
    "get_version",
    "increment_failed_logins",
    "increment_asset_usage",
    "list_assets_by_user",
    "list_attachments_by_run",
    "list_attachments_by_session",
    "list_templates",
    "list_versions",
    "log_command",
    "log_key_usage",
    "mark_user_verified",
    "merge_guest_data",
    "reset_failed_logins",
    "revoke_all_user_tokens",
    "revoke_token_family",
    "save_message",
    "set_asset_indexed",
    "test_api_key_connection",
    "update_message_content",
    "update_message_versions",
    "update_api_key",
    "update_password",
    "update_prompt",
    "update_run_result",
    "update_run_status",
    "update_session_title",
]
