"""Simple Redis-based async cache with TTL for frequently-accessed config data.

Usage:
    from core.infra.cache import get_cache

    cache = get_cache()
    cached = await cache.get("key")
    if cached is None:
        cached = await fetch_from_db()
        await cache.set("key", cached, ttl_seconds=300)
"""

from __future__ import annotations

import json
import os
from typing import Any

from core.env import env_int
from core.infra.logging_config import get_logger

logger = get_logger(__name__)

CACHE_PREFIX = os.environ.get("REDIS_CACHE_PREFIX", "cache:")
CACHE_ENABLED = os.environ.get("REDIS_CACHE_ENABLED", "1") == "1"
DEFAULT_TTL = env_int("REDIS_CACHE_TTL", 300)


class Cache:
    """Redis-backed async cache with JSON serialization and configurable TTL."""

    def __init__(self) -> None:
        self._redis: Any = None

    async def _ensure_redis(self) -> Any:
        if self._redis is None:
            from broker import get_redis

            self._redis = get_redis()
        return self._redis

    def _key(self, name: str) -> str:
        return f"{CACHE_PREFIX}{name}"

    async def get(self, name: str) -> Any | None:
        """Return the cached JSON value for a name, or None if missing or disabled."""
        if not CACHE_ENABLED:
            return None
        try:
            r = await self._ensure_redis()
            raw = await r.get(self._key(name))
            if raw is None:
                return None
            return json.loads(raw)
        except Exception:
            logger.debug("Cache get failed for %s", name, exc_info=True)
            return None

    async def set(
        self, name: str, value: Any, ttl_seconds: int = DEFAULT_TTL
    ) -> None:
        """Cache a JSON-serializable value under a name with a TTL in seconds."""
        if not CACHE_ENABLED:
            return
        try:
            r = await self._ensure_redis()
            await r.set(self._key(name), json.dumps(value, ensure_ascii=False),
                        ex=ttl_seconds)
        except Exception:
            logger.debug("Cache set failed for %s", name, exc_info=True)

    async def delete(self, name: str) -> None:
        """Remove a cached value by name."""
        if not CACHE_ENABLED:
            return
        try:
            r = await self._ensure_redis()
            await r.delete(self._key(name))
        except Exception:
            logger.debug("Cache delete failed for %s", name, exc_info=True)

    async def invalidate_pattern(self, pattern: str) -> None:
        """Delete all keys matching a pattern (use sparingly in production)."""
        if not CACHE_ENABLED:
            return
        try:
            r = await self._ensure_redis()
            cursor = 0
            full_pattern = f"{CACHE_PREFIX}{pattern}"
            while True:
                cursor, keys = await r.scan(cursor, match=full_pattern, count=100)
                if keys:
                    await r.delete(*keys)
                if cursor == 0:
                    break
        except Exception:
            logger.debug("Cache invalidate failed for %s", pattern, exc_info=True)


_cache: Cache | None = None


def get_cache() -> Cache:
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache
