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

    # "anonymous" never returns keys directly — it only serves as the fallback
    # source for other users (see get_api_keys implementation).
    keys_direct = await get_api_keys("anonymous")
    assert keys_direct == []


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
            usage_type="llm",
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

    await create_api_key("user1", "openai", usage_type="embedding", plaintext_key="sk-emb")
    result = await get_embedding_api_key()
    assert result == "sk-emb"


@pytest.mark.asyncio
async def test_get_embedding_api_key_both(db_engine):
    from repository.keys_crud import create_api_key, get_embedding_api_key

    await create_api_key("user1", "openai", usage_type="both", plaintext_key="sk-both")
    result = await get_embedding_api_key()
    assert result == "sk-both"


@pytest.mark.asyncio
async def test_get_embedding_api_key_none(db_engine):
    from repository.keys_crud import get_embedding_api_key

    result = await get_embedding_api_key()
    assert result is None


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

    from core.infra.database import KeyUsageLog, get_session_factory
    from uuid import uuid4
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
        usage_type="embedding",
    )
    assert result is not None
    assert result["usage_type"] == "embedding"


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
    from repository.keys_crud import create_api_key, get_api_keys
    from core.infra.database import UserApiKey, get_session_factory
    from datetime import UTC, datetime

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
