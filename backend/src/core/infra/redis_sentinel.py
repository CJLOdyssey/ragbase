"""Redis Sentinel high-availability integration.

When REDIS_SENTINEL_ENABLED=1, uses redis-py Sentinel client to discover
the current master.  Otherwise falls back to a direct REDIS_URL connection.
"""

from __future__ import annotations

import os
from typing import Any

from redis.asyncio import Redis as AsyncRedis
from redis.asyncio.sentinel import Sentinel

SENTINEL_ENABLED = os.environ.get("REDIS_SENTINEL_ENABLED", "").lower() in ("1", "true", "yes")
SENTINEL_HOSTS_STR = os.environ.get("REDIS_SENTINEL_HOSTS", "sentinel-1:26379,sentinel-2:26380,sentinel-3:26381")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")
SERVICE_NAME = os.environ.get("REDIS_SENTINEL_SERVICE", "agent-studio-redis")
SENTINEL_DB = int(os.environ.get("REDIS_SENTINEL_DB", "0"))

_sentinel: Sentinel | None = None


def _get_sentinel() -> Sentinel:
    """Return (lazily creating) the global Sentinel client."""
    global _sentinel
    if _sentinel is None:
        hosts = [
            (h.rsplit(":", 1)[0], int(h.rsplit(":", 1)[1]))
            for h in SENTINEL_HOSTS_STR.split(",")
        ]
        kwargs: dict[str, Any] = {
            "decode_responses": True,
            "socket_keepalive": True,
            "socket_connect_timeout": 10,
        }
        if REDIS_PASSWORD:
            kwargs["password"] = REDIS_PASSWORD
        _sentinel = Sentinel(hosts, **kwargs)
    return _sentinel


def create_redis() -> Any:
    """Create an AsyncRedis connection.

    Uses Sentinel discovery when REDIS_SENTINEL_ENABLED is set; otherwise
    falls back to a direct connection via REDIS_URL.
    """
    if SENTINEL_ENABLED:
        sentinel = _get_sentinel()
        max_connections = int(os.environ.get("REDIS_POOL_SIZE", "20"))
        kwargs: dict[str, Any] = {
            "db": SENTINEL_DB,
            "decode_responses": True,
            "socket_keepalive": True,
            "socket_connect_timeout": 10,
            "health_check_interval": 30,
            "retry_on_timeout": True,
            "max_connections": max_connections,
        }
        if REDIS_PASSWORD:
            kwargs["password"] = REDIS_PASSWORD
        return sentinel.master_for(SERVICE_NAME, **kwargs)

    # Direct connection — read REDIS_URL from env to avoid circular imports
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    max_connections = int(os.environ.get("REDIS_POOL_SIZE", "20"))
    return AsyncRedis.from_url(
        url,
        max_connections=max_connections,
        decode_responses=True,
        socket_keepalive=True,
        socket_connect_timeout=10,
        health_check_interval=30,
        retry_on_timeout=True,
    )
