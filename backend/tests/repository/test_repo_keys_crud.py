"""Unit tests for backend/repository/keys_crud.py — direct repo function tests."""

import os

import pytest

os.environ.setdefault("KEY_VAULT_SECRET", "0123456789abcdef0123456789abcdef")
os.environ["AUTH_MODE"] = "legacy"
os.environ["AUTH_ENABLED"] = "0"
os.environ["RATE_LIMIT"] = "9999"
os.environ["CHECKPOINTER_BACKEND"] = "memory"
os.environ["DATABASE_POOL_SIZE"] = "0"


@pytest.mark.asyncio
async def test_create_api_key_default_clears_others(db_engine):
    from repository.keys_crud import create_api_key

    key1 = await create_api_key("user1", "openai", plaintext_key="sk-key-1", is_default=True)
    assert key1.is_default is True

    key2 = await create_api_key("user1", "deepseek", plaintext_key="sk-key-2", is_default=True)
    assert key2.is_default is True

    from core.infra.database import UserApiKey, get_session_factory
    factory = get_session_factory()
    async with factory() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(UserApiKey).where(UserApiKey.user_id == "user1", UserApiKey.is_default)
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].id == key2.id


@pytest.mark.asyncio
async def test_get_api_keys_with_fallback(db_engine):
    from repository.keys_crud import create_api_key, get_api_keys

    await create_api_key("anonymous", "openai", plaintext_key="sk-anon-key-12345")
    keys = await get_api_keys("someuser")
    assert len(keys) > 0
    assert keys[0]["provider"] == "openai"
    assert "..." in keys[0]["key_masked"]

    # "anonymous" is a real key namespace: with AUTH_ENABLED, every
    # unauthenticated request resolves to it, so guests must see these keys
    # directly (guest-configured + pre-configured defaults) or guest chat
    # silently fails with "no API key".
    keys_direct = await get_api_keys("anonymous")
    assert len(keys_direct) > 0
    assert keys_direct[0]["provider"] == "openai"


@pytest.mark.asyncio
async def test_get_api_keys_no_fallback_for_anonymous(db_engine):
    from repository.keys_crud import get_api_keys

    keys = await get_api_keys("anonymous")
    assert keys == []


@pytest.mark.asyncio
async def test_get_api_keys_decrypt_failure_graceful(db_engine):
    from core.infra.database import UserApiKey, get_session_factory
    from repository.keys_crud import get_api_keys

    factory = get_session_factory()
    async with factory() as session:
        obj = UserApiKey(
            id="bad-key-id-1234",
            user_id="user1",
            provider="openai",
            capabilities=["llm"],
            label="bad",
            encrypted_key="not-valid-fernet",
            models="",
            is_active=True,
        )
        session.add(obj)
        await session.commit()

    keys = await get_api_keys("user1")
    assert len(keys) == 1
    assert "解密失败" in keys[0]["key_masked"]


@pytest.mark.asyncio
async def test_get_api_key_for_use_found(db_engine):
    from repository.keys_crud import create_api_key, get_api_key_for_use

    k = await create_api_key("user1", "openai", plaintext_key="sk-real-key-xyz")
    result = await get_api_key_for_use(k.id, "user1")
    assert result is not None
    assert result["api_key"] == "sk-real-key-xyz"
    assert result["provider"] == "openai"


@pytest.mark.asyncio
async def test_get_api_key_for_use_not_found(db_engine):
    from repository.keys_crud import get_api_key_for_use

    result = await get_api_key_for_use("nonexistent", "user1")
    assert result is None


@pytest.mark.asyncio
async def test_get_api_key_for_use_anonymous_fallback(db_engine):
    from repository.keys_crud import create_api_key, get_api_key_for_use

    k = await create_api_key("anonymous", "openai", plaintext_key="sk-anon-key")
    result = await get_api_key_for_use(k.id, "someuser")
    assert result is not None
    assert result["api_key"] == "sk-anon-key"


@pytest.mark.asyncio
async def test_get_api_key_for_use_inactive_returns_none(db_engine):
    from repository.keys_crud import create_api_key, get_api_key_for_use, update_api_key

    k = await create_api_key("user1", "openai", plaintext_key="sk-test")
    await update_api_key(k.id, "user1", is_active=False)
    result = await get_api_key_for_use(k.id, "user1")
    assert result is None


@pytest.mark.asyncio
async def test_update_api_key_partial(db_engine):
    from repository.keys_crud import create_api_key, update_api_key

    k = await create_api_key("user1", "openai", plaintext_key="sk-original", label="old")
    result = await update_api_key(k.id, "user1", label="new-label")
    assert result is not None
    assert result["label"] == "new-label"


@pytest.mark.asyncio
async def test_update_api_key_not_found(db_engine):
    from repository.keys_crud import update_api_key

    result = await update_api_key("nonexistent", "user1", label="test")
    assert result is None


@pytest.mark.asyncio
async def test_update_api_key_wrong_owner(db_engine):
    from repository.keys_crud import create_api_key, update_api_key

    k = await create_api_key("user1", "openai", plaintext_key="sk-test")
    result = await update_api_key(k.id, "otheruser", label="hacked")
    assert result is None


@pytest.mark.asyncio
async def test_update_api_key_anonymous_fallback(db_engine):
    from repository.keys_crud import create_api_key, update_api_key

    k = await create_api_key("anonymous", "openai", plaintext_key="sk-anon")
    result = await update_api_key(k.id, "realuser", label="adopted")
    assert result is not None
    assert result["label"] == "adopted"


@pytest.mark.asyncio
async def test_update_api_key_reencrypt(db_engine):
    from repository.keys_crud import create_api_key, update_api_key

    k = await create_api_key("user1", "openai", plaintext_key="sk-original")
    result = await update_api_key(k.id, "user1", plaintext_key="sk-new-value")
    assert result is not None


@pytest.mark.asyncio
async def test_update_api_key_default_clears_others(db_engine):
    from repository.keys_crud import create_api_key, update_api_key

    await create_api_key("user1", "openai", plaintext_key="sk-1", is_default=True)
    k2 = await create_api_key("user1", "deepseek", plaintext_key="sk-2")

    await update_api_key(k2.id, "user1", is_default=True)

    from core.infra.database import UserApiKey, get_session_factory
    factory = get_session_factory()
    async with factory() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(UserApiKey).where(UserApiKey.user_id == "user1", UserApiKey.is_default)
        )
        defaults = result.scalars().all()
        assert len(defaults) == 1
        assert defaults[0].id == k2.id


@pytest.mark.asyncio
async def test_delete_api_key(db_engine):
    from repository.keys_crud import create_api_key, delete_api_key

    k = await create_api_key("user1", "openai", plaintext_key="sk-del")
    assert await delete_api_key(k.id, "user1") is True
    assert await delete_api_key(k.id, "user1") is False


@pytest.mark.asyncio
async def test_delete_api_key_not_found(db_engine):
    from repository.keys_crud import delete_api_key

    assert await delete_api_key("nonexistent", "user1") is False


@pytest.mark.asyncio
async def test_delete_api_key_wrong_owner(db_engine):
    from repository.keys_crud import create_api_key, delete_api_key

    k = await create_api_key("user1", "openai", plaintext_key="sk-del")
    assert await delete_api_key(k.id, "otheruser") is False


@pytest.mark.asyncio
async def test_delete_api_key_anonymous_fallback(db_engine):
    from repository.keys_crud import create_api_key, delete_api_key

    k = await create_api_key("anonymous", "openai", plaintext_key="sk-del")
    assert await delete_api_key(k.id, "realuser") is True


@pytest.mark.asyncio
async def test_get_default_api_key(db_engine):
    from repository.keys_crud import create_api_key, get_default_api_key

    await create_api_key("user1", "openai", plaintext_key="sk-def", is_default=True)
    result = await get_default_api_key("user1")
    assert result is not None
    assert result["api_key"] == "sk-def"


@pytest.mark.asyncio
async def test_get_default_api_key_fallback_anonymous(db_engine):
    from repository.keys_crud import create_api_key, get_default_api_key

    await create_api_key("anonymous", "openai", plaintext_key="sk-anon-def", is_default=True)
    result = await get_default_api_key("someuser")
    assert result is not None
    assert result["api_key"] == "sk-anon-def"


@pytest.mark.asyncio
async def test_get_default_api_key_none(db_engine):
    from repository.keys_crud import get_default_api_key

    result = await get_default_api_key("someuser")
    assert result is None


@pytest.mark.asyncio
async def test_get_default_api_key_guest_fallback(db_engine):
    from repository.keys_crud import create_api_key, get_default_api_key

    await create_api_key("u_guest1", "openai", plaintext_key="sk-guest-def", is_default=True)
    result = await get_default_api_key("u_guest1")
    assert result is not None
    assert result["api_key"] == "sk-guest-def"


@pytest.mark.asyncio
async def test_get_default_api_key_system_wide_fallback(db_engine):
    from repository.keys_crud import create_api_key, get_default_api_key

    await create_api_key("otheruser", "openai", plaintext_key="sk-other", is_default=True)
    result = await get_default_api_key("u_newguest_xyz")
    assert result is not None


@pytest.mark.asyncio
async def test_get_embedding_api_key(db_engine):
    from repository.keys_crud import create_api_key, get_embedding_api_key

    await create_api_key("user1", "openai", capabilities=["embedding"], plaintext_key="sk-emb")
    result = await get_embedding_api_key()
    assert result == "sk-emb"


@pytest.mark.asyncio
async def test_get_embedding_api_key_both(db_engine):
    from repository.keys_crud import create_api_key, get_embedding_api_key

    await create_api_key("user1", "openai", capabilities=["llm", "embedding"], plaintext_key="sk-both")
    result = await get_embedding_api_key()
    assert result == "sk-both"


@pytest.mark.asyncio
async def test_get_embedding_api_key_none(db_engine):
    from repository.keys_crud import get_embedding_api_key

    result = await get_embedding_api_key()
    assert result is None


@pytest.mark.asyncio
async def test_get_embedding_api_key_beyond_row_window(db_engine):
    """SQL-side filtering must find a matching key beyond the old 50-row window."""
    from repository.keys_crud import create_api_key, get_embedding_api_key

    for i in range(60):
        await create_api_key("user1", "openai", plaintext_key=f"sk-llm-{i}")
    await create_api_key("user1", "openai", capabilities=["embedding"], plaintext_key="sk-emb-60")
    result = await get_embedding_api_key()
    assert result == "sk-emb-60"


@pytest.mark.asyncio
async def test_get_embedding_config_prefers_embedding_model_key(db_engine):
    """A key whose models list names an embedding model wins over an older bare key."""
    from repository.keys_crud import create_api_key, get_embedding_config

    # Older key: embedding capability but LLM-only models.
    await create_api_key(
        "user1", "custom", capabilities=["embedding"],
        plaintext_key="sk-deepseek", base_url="https://api.deepseek.com",
        models=["deepseek-v4-flash"],
    )
    # Newer key: siliconflow with bge-m3.
    await create_api_key(
        "user1", "custom", capabilities=["embedding"],
        plaintext_key="sk-silicon", base_url="https://api.siliconflow.cn/v1",
        models=["BAAI/bge-m3", "deepseek-ai/DeepSeek-V4"],
    )

    cfg = await get_embedding_config()
    assert cfg is not None
    assert cfg["api_key"] == "sk-silicon"
    assert cfg["base_url"] == "https://api.siliconflow.cn/v1"
    assert cfg["model"] == "BAAI/bge-m3"


@pytest.mark.asyncio
async def test_get_embedding_config_falls_back_to_oldest(db_engine):
    """No embedding-named models → oldest embedding-capability key, DashScope defaults."""
    from repository.keys_crud import create_api_key, get_embedding_config

    await create_api_key("user1", "dashscope", capabilities=["embedding"], plaintext_key="sk-old")
    await create_api_key("user1", "custom", capabilities=["embedding"], plaintext_key="sk-new")

    cfg = await get_embedding_config()
    assert cfg == {"api_key": "sk-old", "base_url": None, "model": "text-embedding-v3"}


@pytest.mark.asyncio
async def test_get_tool_api_key_matches_capabilities(db_engine):
    """A key carrying the tool capability is served for its provider."""
    from repository.keys_crud import create_api_key, get_tool_api_key

    await create_api_key("user1", "tavily", capabilities=["tool"], plaintext_key="tavily-secret")
    result = await get_tool_api_key("tavily")
    assert result == "tavily-secret"


@pytest.mark.asyncio
async def test_get_tool_api_key_requires_tool_capability(db_engine):
    """Provider match alone is not enough — the key must carry the tool capability."""
    from repository.keys_crud import create_api_key, get_tool_api_key

    await create_api_key("user1", "tavily", plaintext_key="tavily-llm-only")
    result = await get_tool_api_key("tavily")
    assert result is None


@pytest.mark.asyncio
async def test_get_tool_api_key_provider_scope(db_engine):
    """A tool-capable key of another provider is not served for this provider."""
    from repository.keys_crud import create_api_key, get_tool_api_key

    await create_api_key("user1", "openai", capabilities=["tool"], plaintext_key="openai-tool")
    assert await get_tool_api_key("tavily") is None
    assert await get_tool_api_key("openai") == "openai-tool"


@pytest.mark.asyncio
async def test_log_key_usage(db_engine):
    from repository.keys_crud import create_api_key, log_key_usage

    k = await create_api_key("user1", "openai", plaintext_key="sk-log")
    await log_key_usage(k.id, "user1", "run-1", "openai", "gpt-4", tokens_prompt=10, tokens_completion=20)

    from core.infra.database import KeyUsageLog, get_session_factory
    factory = get_session_factory()
    async with factory() as session:
        from sqlalchemy import select
        result = await session.execute(select(KeyUsageLog))
        logs = result.scalars().all()
        assert len(logs) == 1
        assert logs[0].tokens_total == 30


@pytest.mark.asyncio
async def test_log_key_usage_with_error(db_engine):
    from repository.keys_crud import log_key_usage

    await log_key_usage(
        None, "user1", "run-2", "openai", "gpt-4",
        tokens_prompt=0, tokens_completion=0, status="error",
        error_message="timeout"
    )

    from core.infra.database import KeyUsageLog, get_session_factory
    factory = get_session_factory()
    async with factory() as session:
        from sqlalchemy import select
        result = await session.execute(select(KeyUsageLog))
        log = result.scalar_one()
        assert log.status == "error"
        assert log.error_message == "timeout"


@pytest.mark.asyncio
async def test_get_key_usage_stats(db_engine):
    from repository.keys_crud import create_api_key, get_key_usage_stats

    k = await create_api_key("user1", "openai", plaintext_key="sk-stat")

    from uuid import uuid4

    from core.infra.database import KeyUsageLog, get_session_factory
    factory = get_session_factory()
    async with factory() as session:
        log = KeyUsageLog(
            id=str(uuid4()),
            key_id=k.id,
            user_id="user1",
            run_id="r1",
            provider="openai",
            model="gpt-4",
            tokens_prompt=50,
            tokens_completion=50,
            tokens_total=100,
            status="success",
        )
        session.add(log)
        await session.commit()

    stats = await get_key_usage_stats("user1")
    assert stats["today_requests"] >= 1
    assert stats["today_tokens"] >= 100


@pytest.mark.asyncio
async def test_get_key_usage_stats_all_users(db_engine):
    from repository.keys_crud import get_key_usage_stats

    stats = await get_key_usage_stats()
    assert "today_requests" in stats
    assert "month_tokens" in stats


@pytest.mark.asyncio
async def test_get_key_usage_stats_anonymous(db_engine):
    from repository.keys_crud import get_key_usage_stats

    stats = await get_key_usage_stats("anonymous")
    assert "today_requests" in stats


@pytest.mark.asyncio
async def test_update_api_key_base_url_and_models(db_engine):
    from repository.keys_crud import create_api_key, update_api_key

    k = await create_api_key("user1", "openai", plaintext_key="sk-test", base_url="http://old")
    result = await update_api_key(
        k.id, "user1",
        base_url="http://new",
        models=["gpt-4", "gpt-3.5-turbo"],
        capabilities=["embedding"],
    )
    assert result is not None
    assert result["capabilities"] == ["embedding"]


@pytest.mark.asyncio
async def test_update_api_key_set_inactive(db_engine):
    from repository.keys_crud import create_api_key, update_api_key

    k = await create_api_key("user1", "openai", plaintext_key="sk-active")
    result = await update_api_key(k.id, "user1", is_active=False)
    assert result is not None
    assert result["is_active"] is False


@pytest.mark.asyncio
async def test_get_api_keys_with_models(db_engine):
    from repository.keys_crud import create_api_key, get_api_keys

    await create_api_key(
        "user1", "openai", plaintext_key="sk-models",
        models=["gpt-4", "gpt-3.5-turbo"],
    )
    keys = await get_api_keys("user1")
    assert len(keys) == 1
    assert keys[0]["models"] == ["gpt-4", "gpt-3.5-turbo"]


@pytest.mark.asyncio
async def test_create_api_key_with_model_types_serialized(db_engine):
    from repository.keys_crud import create_api_key, get_api_keys

    await create_api_key(
        "user1", "custom", plaintext_key="sk-mt",
        models=["gpt-4o"], model_types={"gpt-4o": "embedding"},
    )
    keys = await get_api_keys("user1")
    assert len(keys) == 1
    assert keys[0]["model_types"] == {"gpt-4o": "embedding"}


@pytest.mark.asyncio
async def test_get_api_keys_model_types_none_by_default(db_engine):
    from repository.keys_crud import create_api_key, get_api_keys

    await create_api_key("user1", "custom", plaintext_key="sk-nomt", models=["gpt-4o"])
    keys = await get_api_keys("user1")
    assert len(keys) == 1
    assert keys[0]["model_types"] is None


@pytest.mark.asyncio
async def test_update_api_key_model_types_replace(db_engine):
    from repository.keys_crud import create_api_key, get_api_keys, update_api_key

    k = await create_api_key(
        "user1", "custom", plaintext_key="sk-upd", models=["gpt-4o"],
        model_types={"gpt-4o": "embedding"},
    )
    result = await update_api_key(k.id, "user1", model_types={"gpt-4o": "rerank"})
    assert result is not None
    assert result["model_types"] == {"gpt-4o": "rerank"}

    keys = await get_api_keys("user1")
    assert keys[0]["model_types"] == {"gpt-4o": "rerank"}


@pytest.mark.asyncio
async def test_update_api_key_model_types_clear(db_engine):
    from repository.keys_crud import create_api_key, update_api_key

    k = await create_api_key(
        "user1", "custom", plaintext_key="sk-clr", models=["gpt-4o"],
        model_types={"gpt-4o": "embedding"},
    )
    result = await update_api_key(k.id, "user1", model_types={})
    assert result is not None
    assert result["model_types"] == {}


@pytest.mark.asyncio
async def test_get_api_keys_empty_models(db_engine):
    from repository.keys_crud import create_api_key, get_api_keys

    await create_api_key("user1", "openai", plaintext_key="sk-no-models")
    keys = await get_api_keys("user1")
    assert len(keys) == 1
    assert keys[0]["models"] == []


@pytest.mark.asyncio
async def test_get_api_key_for_use_models_list(db_engine):
    from repository.keys_crud import create_api_key, get_api_key_for_use

    k = await create_api_key(
        "user1", "openai", plaintext_key="sk-models",
        models=["gpt-4", "o1-preview"],
    )
    result = await get_api_key_for_use(k.id, "user1")
    assert result is not None
    assert "gpt-4" in result["models"]


@pytest.mark.asyncio
async def test_get_api_keys_with_last_used_at(db_engine):
    from datetime import UTC, datetime

    from core.infra.database import UserApiKey, get_session_factory
    from repository.keys_crud import create_api_key, get_api_keys

    k = await create_api_key("user1", "openai", plaintext_key="sk-lastused")
    factory = get_session_factory()
    async with factory() as session:
        obj = await session.get(UserApiKey, k.id)
        obj.last_used_at = datetime.now(UTC)
        await session.commit()

    keys = await get_api_keys("user1")
    assert len(keys) == 1
    assert keys[0]["last_used_at"] is not None


@pytest.mark.asyncio
async def test_get_default_api_key_non_guest_no_fallback(db_engine):
    """Non-guest user with no keys and no anonymous keys returns None."""
    from repository.keys_crud import get_default_api_key

    result = await get_default_api_key("regular_user_123")
    assert result is None


@pytest.mark.asyncio
async def test_get_default_api_key_anonymous_user_no_keys(db_engine):
    """anonymous user with no keys returns None."""
    from repository.keys_crud import get_default_api_key

    result = await get_default_api_key("anonymous")
    assert result is None


@pytest.mark.asyncio
async def test_get_api_key_for_model_matches_models_list(db_engine):
    """A key whose models list contains the requested model is returned."""
    from repository.keys_crud import create_api_key, get_api_key_for_model

    await create_api_key("user1", "custom", plaintext_key="sk-deepseek", base_url="https://api.deepseek.com", models=["deepseek-v4-flash"], is_default=False)
    sf = await create_api_key("user1", "custom", plaintext_key="sk-siliconflow", base_url="https://api.siliconflow.cn/v1", models=["Qwen/Qwen3-8B", "deepseek-ai/DeepSeek-V4-Flash"], is_default=False)

    result = await get_api_key_for_model("Qwen/Qwen3-8B", "user1")
    assert result is not None
    assert result["id"] == sf.id
    assert result["base_url"] == "https://api.siliconflow.cn/v1"


@pytest.mark.asyncio
async def test_get_api_key_for_model_substring_does_not_match(db_engine):
    """Model lookup must match a full comma-separated entry, not a substring."""
    from repository.keys_crud import create_api_key, get_api_key_for_model

    await create_api_key("user1", "custom", plaintext_key="sk-deepseek", base_url="https://api.deepseek.com", models=["deepseek-v4-flash"], is_default=False)

    # "deepseek-v4-flash" as a substring would naively match "deepseek-v4-flash-x"
    assert await get_api_key_for_model("deepseek-v4-flash-x", "user1") is None
    assert await get_api_key_for_model("unknown-model", "user1") is None


@pytest.mark.asyncio
async def test_get_api_key_for_model_anonymous_fallback(db_engine):
    """Non-guest users fall back to anonymous keys when they have none of their own."""
    from repository.keys_crud import create_api_key, get_api_key_for_model

    await create_api_key("anonymous", "custom", plaintext_key="sk-anon-sf", base_url="https://api.siliconflow.cn/v1", models=["Qwen/Qwen3-8B"], is_default=False)

    result = await get_api_key_for_model("Qwen/Qwen3-8B", "some_user_123")
    assert result is not None
    assert result["base_url"] == "https://api.siliconflow.cn/v1"
