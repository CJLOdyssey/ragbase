"""Unit tests for core.infra.cache — Redis-backed TTL cache facade."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    store: dict[str, str] = {}
    r.get.side_effect = lambda k: store.get(k)
    r.set.side_effect = lambda k, v, **kw: store.update({k: v}) or True
    r.delete.side_effect = lambda *ks: [store.pop(k, None) for k in ks]
    return r


class TestCache:
    @pytest.mark.asyncio
    async def test_get_hit_and_miss(self, mock_redis):
        from core.infra.cache import Cache

        cache = Cache()
        with patch.object(cache, "_ensure_redis", new_callable=AsyncMock, return_value=mock_redis):
            assert await cache.get("missing") is None
            await cache.set("key", {"a": 1})
            assert await cache.get("key") == {"a": 1}

    @pytest.mark.asyncio
    async def test_set_uses_prefix_and_ttl(self, mock_redis):
        from core.infra.cache import Cache

        cache = Cache()
        with patch.object(cache, "_ensure_redis", new_callable=AsyncMock, return_value=mock_redis):
            await cache.set("key", "value", ttl_seconds=60)
            mock_redis.set.assert_awaited_once_with("cache:key", '"value"', ex=60)

    @pytest.mark.asyncio
    async def test_delete(self, mock_redis):
        from core.infra.cache import Cache

        cache = Cache()
        with patch.object(cache, "_ensure_redis", new_callable=AsyncMock, return_value=mock_redis):
            await cache.set("key", "value")
            await cache.delete("key")
            assert await cache.get("key") is None

    @pytest.mark.asyncio
    async def test_invalidate_pattern_scans_and_deletes(self, mock_redis):
        from core.infra.cache import Cache

        cache = Cache()
        with patch.object(cache, "_ensure_redis", new_callable=AsyncMock, return_value=mock_redis):
            await cache.set("agents:1", "a")
            await cache.set("agents:2", "b")
            await cache.set("other", "c")

            scan_calls = [(0, {"cache:agents:1", "cache:agents:2"})]
            mock_redis.scan.side_effect = lambda cursor, **kw: scan_calls.pop(0)
            await cache.invalidate_pattern("agents:*")

            assert await cache.get("agents:1") is None
            assert await cache.get("agents:2") is None
            assert await cache.get("other") == "c"

    @pytest.mark.asyncio
    async def test_redis_failure_degrades_to_none(self, mock_redis):
        from core.infra.cache import Cache

        cache = Cache()
        mock_redis.get.side_effect = ConnectionError("down")
        with patch.object(cache, "_ensure_redis", new_callable=AsyncMock, return_value=mock_redis):
            assert await cache.get("key") is None

    @pytest.mark.asyncio
    async def test_disabled_cache_is_noop(self):
        from core.infra import cache as cache_mod

        with patch.object(cache_mod, "CACHE_ENABLED", False):
            cache = cache_mod.Cache()
            assert await cache.get("key") is None
            await cache.set("key", "value")
            await cache.delete("key")

    def test_get_cache_singleton(self):
        from core.infra.cache import get_cache

        assert get_cache() is get_cache()
