"""Messaging infrastructure: Celery app + Redis pub/sub for streaming."""

import asyncio
import contextlib
import inspect
import json
import os
from collections.abc import AsyncIterator
from typing import Any

from celery import Celery
from core.infra.logging_config import get_logger
from redis.asyncio import Redis as AsyncRedis  # noqa: F401  # re-exported for backward compat

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Celery app
# ---------------------------------------------------------------------------

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6380/0")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6380/0")

celery_app = Celery(
    "backend",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=600,
    task_time_limit=900,
)

celery_app.autodiscover_tasks(["tasks"])

# Periodic reindex sweep: catch assets whose files changed after indexing.
celery_app.conf.beat_schedule = {
    "reindex-sweep": {
        "task": "tasks.registry.reindex_sweep",
        "schedule": 300.0,
    },
}

# ---------------------------------------------------------------------------
# Redis pub/sub
# ---------------------------------------------------------------------------

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6380/0")

# Per-event-loop connection pool — Celery prefork workers create a new event
# loop via asyncio.run() in each child process, so a single global pool bound
# to the parent's loop becomes invalid ("Event loop is closed").
#
# Keyed by the loop OBJECT (not id()): asyncio.run() creates a fresh loop per
# task; after the task the loop is garbage-collected and its id() can be
# REUSED by the next task's loop. Keying by id() then hits the stale pool
# whose connections belong to a closed loop -> redis calls hang forever.
# Keying by the loop object and dropping entries whose loop is gone fixes
# both the stale-hit and the leak (socket_timeout on the pool is a last-resort
# guard against a hung-but-connected Redis).
_pools: dict[asyncio.AbstractEventLoop, Any] = {}
CHANNEL_PREFIX = "run:"


def _channel(run_id: str) -> str:
    return f"{CHANNEL_PREFIX}{run_id}"


def get_redis() -> Any:  # returns AsyncRedis
    """Return an AsyncRedis pool for the current event loop.

    Each asyncio event loop gets its own connection pool so that Celery's
    prefork model (where every asyncio.run() call creates a fresh loop) works
    correctly.

    When REDIS_SENTINEL_ENABLED is set, creates the connection via
    Sentinel discovery; otherwise falls back to a direct REDIS_URL connection.
    """

    loop = asyncio.get_running_loop()

    # Drop stale pools whose loop is no longer running (loop object identity,
    # NOT id() — id reuse after GC would otherwise hit dead connections).
    stale = [k for k in _pools if k is not loop and (k.is_closed() or not k.is_running())]
    for k in stale:
        _pools.pop(k, None)

    pool = _pools.get(loop)
    if pool is None:
        from core.infra.redis_sentinel import create_redis

        pool = create_redis()
        _pools[loop] = pool
    return pool


async def close_redis() -> None:
    """Close the Redis connection pool for the current event loop."""

    loop = asyncio.get_running_loop()
    pool = _pools.pop(loop, None)
    if pool is not None:
        # Shutdown-path defense: tolerate pools injected by test mocks
        # (MagicMock has no awaitable aclose), never crash teardown.
        close = getattr(pool, "aclose", None)
        if close is not None:
            result = close()
            if inspect.isawaitable(result):
                await result


async def publish_run_message(run_id: str, message: dict[str, Any]) -> None:
    """Publish a message to a run's Redis pub/sub channel."""
    r = get_redis()
    await r.publish(_channel(run_id), json.dumps(message, ensure_ascii=False))


async def subscribe_run(run_id: str) -> AsyncIterator[dict[str, Any]]:
    """Subscribe to a run's pub/sub channel.

    Uses redis-py pubsub.listen() with socket_keepalive enabled on the
    underlying connection to prevent TCP idle timeouts from firewalls/proxies.
    """
    r = get_redis()
    pubsub = r.pubsub()
    try:
        # subscribe inside try: a failing subscribe (pool exhausted) must not
        # leak the pubsub/connection — finally closes it.
        await pubsub.subscribe(_channel(run_id))
        while True:
            try:
                msg = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=None),
                    timeout=60.0,
                )
            except TimeoutError:
                return  # idle keepalive window exhausted — stop the stream
            if msg and msg["type"] == "message":
                data = msg["data"]
                if isinstance(data, str):
                    payload = json.loads(data)
                    yield payload
                    if payload.get("type") == "result":
                        return  # run finished — close the stream
    finally:
        with contextlib.suppress(Exception):
            await pubsub.unsubscribe(_channel(run_id))
        with contextlib.suppress(Exception):
            await pubsub.close()


def _user_channel(user_id: str) -> str:
    return f"user:{user_id}:events"


async def publish_user_event(user_id: str, event: dict[str, Any]) -> None:
    """Publish a domain event to a user's cross-client event channel.

    Fail-open: a Redis outage must never break the primary request path.
    """
    try:
        r = get_redis()
        await r.publish(_user_channel(user_id), json.dumps(event, ensure_ascii=False))
    except Exception:
        logger.debug("publish_user_event failed for %s", user_id, exc_info=True)


async def subscribe_user_events(user_id: str) -> AsyncIterator[dict[str, Any]]:
    """Yield domain events published for *user_id*. Caller cancels to stop."""
    r = get_redis()
    pubsub = r.pubsub()
    try:
        # subscribe inside try: a failing subscribe (pool exhausted) must not
        # leak the pubsub/connection — finally closes it.
        await pubsub.subscribe(_user_channel(user_id))
        while True:
            try:
                msg = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=None),
                    timeout=60.0,
                )
            except TimeoutError:
                continue  # idle keepalive; connection health-checked by redis-py
            if msg and msg["type"] == "message":
                try:
                    yield json.loads(msg["data"])
                except (TypeError, ValueError):
                    continue
    finally:
        with contextlib.suppress(Exception):
            await pubsub.close()


# ---------------------------------------------------------------------------
# Pre‑subscription buffer — closes the timing gap between Celery task start
# and WebSocket connect.  The POST handler subscribes before returning so
# early messages (thinking_stream) are never lost.
# ---------------------------------------------------------------------------

_buffers: dict[str, list[dict[str, Any]]] = {}
_buffer_tasks: dict[str, asyncio.Task[Any]] = {}
_lock: asyncio.Lock = asyncio.Lock()


async def buffer_run_messages(run_id: str) -> None:
    """Subscribe to *run_id* and accumulate messages into an in-memory buffer.

    The WebSocket handler later calls :func:`drain_buffer` to replay them.
    Establishes the Redis subscription synchronously before returning so that
    no messages (especially early ``thinking_stream`` chunks) are lost.
    """
    buf: list[dict[str, Any]] = []
    _buffers[run_id] = buf
    logger = get_logger(__name__)

    try:
        r = get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(f"run:{run_id}")
    except Exception:
        # Fail-open: a Redis outage must never 500 the POST /runs request.
        # With the subscription down nothing can be published either, so an
        # empty buffer degrades gracefully (WS drains nothing, run proceeds).
        logger.warning("Redis buffer subscribe failed for run %s; buffering disabled", run_id, exc_info=True)
        return

    async def _worker() -> None:
        try:
            # subscribe() above has already consumed the subscription
            # confirmation, so there is no "subscribe" message to wait for.
            # Listen with an idle timeout — auto-cleanup prevents buffer leaks
            # when the run finishes without a WebSocket connection to drain it.
            #
            # NOTE: get_message() MUST be given timeout=None (blocking). Its
            # default timeout=0 is non-blocking: the outer wait_for would not
            # fire and the loop would busy-spin ~100k iterations/sec, pegging
            # a CPU core for the whole run. timeout=None + wait_for makes the
            # idle timeout fire while health-check PONGs (also returning None)
            # just resume the wait.
            while True:
                try:
                    msg = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True, timeout=None),
                        timeout=60.0,
                    )
                except TimeoutError:
                    logger.info("Buffer idle timeout for run %s — auto-cleanup", run_id)
                    break
                if msg and msg["type"] == "message":
                    data = msg["data"]
                    if isinstance(data, str):
                        parsed = json.loads(data)
                        logger.info(
                            "Buffer received: type=%s content_len=%d thinking_len=%d",
                            parsed.get("type"),
                            len(parsed.get("content", "")),
                            len(parsed.get("thinking", "")),
                        )
                        buf.append(parsed)
        except asyncio.CancelledError:
            pass
        finally:
            # Always release the pubsub connection back to the pool —
            # otherwise each run leaks one Redis connection until the
            # pool (max_connections=20) is exhausted.
            with contextlib.suppress(Exception):
                await pubsub.unsubscribe(f"run:{run_id}")
            with contextlib.suppress(Exception):
                await pubsub.close()
            _buffers.pop(run_id, None)
            _buffer_tasks.pop(run_id, None)

    _buffer_tasks[run_id] = asyncio.create_task(_worker())


def drain_buffer(run_id: str) -> list[dict[str, Any]]:
    """Return and clear the pre‑subscription buffer for *run_id*."""
    return _buffers.pop(run_id, [])


async def stop_buffer(run_id: str) -> None:
    """Cancel the background worker and discard the buffer."""
    _buffers.pop(run_id, None)
    task = _buffer_tasks.pop(run_id, None)
    if task is not None:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
