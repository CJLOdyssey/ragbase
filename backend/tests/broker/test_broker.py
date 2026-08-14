"""Unit tests for backend/broker.py (Redis URL parsing, pub/sub)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest import MonkeyPatch


@pytest.fixture(autouse=True)
def _restore_get_redis(monkeypatch: MonkeyPatch):
    """Undo conftest's session-level patches so broker tests test real logic.

    The test_client fixture patches backend.core.infra.redis_sentinel.create_redis
    for the entire session. Broker tests need the REAL create_redis path.

    Also resets SENTINEL_ENABLED to False — tests in test_redis_sentinel.py use
    importlib.reload() which can leave the module with SENTINEL_ENABLED=True
    after the test ends (monkeypatch restores the env var, but the module-level
    constant is not re-evaluated).

    Teardown clears broker._pools so MagicMock pools seeded by individual tests
    never leak into later tests in the same worker (a TestClient shutdown would
    otherwise call close_redis() → await pool.aclose() on a MagicMock → TypeError).
    """
    import broker as mod_broker
    import core.infra.redis_sentinel as rsmod

    rsmod.SENTINEL_ENABLED = False
    rsmod._sentinel = None

    from tests.conftest import _original_create_redis

    _real_create_redis = _original_create_redis

    def real_get_redis():
        loop = mod_broker.asyncio.get_running_loop()
        loop_id = id(loop)
        pool = mod_broker._pools.get(loop_id)
        if pool is None:
            pool = _real_create_redis()
            mod_broker._pools[loop_id] = pool
        return pool

    monkeypatch.setattr("broker.get_redis", real_get_redis)
    monkeypatch.setattr(
        "core.infra.redis_sentinel.create_redis", _real_create_redis
    )
    yield
    mod_broker._pools.clear()


class TestBrokerRedis:
    def test_redis_url_has_valid_format(self):
        """REDIS_URL should be a valid redis URL (depends on .env / env var)."""
        from broker import REDIS_URL

        assert REDIS_URL.startswith("redis://")
        assert "localhost" in REDIS_URL or "redis" in REDIS_URL

    def test_broker_url_default(self):
        from broker import BROKER_URL

        assert BROKER_URL == "redis://localhost:6380/0"

    def test_channel_format(self):
        from broker import _channel

        assert _channel("run-abc") == "run:run-abc"

    @patch("core.infra.redis_sentinel.AsyncRedis.from_url")
    @patch("broker.asyncio.get_running_loop")
    def test_get_redis_creates_pool(self, mock_loop, mock_from_url, monkeypatch):
        monkeypatch.setenv("REDIS_POOL_SIZE", "20")
        mock_loop.return_value = loop = MagicMock()
        loop_id = id(loop)
        mock_redis = MagicMock()
        mock_from_url.return_value = mock_redis

        # Clean up any existing pools
        from broker import REDIS_URL, _pools

        _pools.clear()

        from broker import get_redis

        result = get_redis()
        mock_from_url.assert_called_once_with(
            REDIS_URL,
            max_connections=20,
            decode_responses=True,
            socket_keepalive=True,
            socket_connect_timeout=10,
            socket_timeout=10,
            health_check_interval=30,
            retry_on_timeout=True,
        )
        assert result == mock_redis
        assert _pools[loop_id] == mock_redis

    @patch("core.infra.redis_sentinel.AsyncRedis.from_url")
    @patch("broker.asyncio.get_running_loop")
    def test_get_redis_reuses_pool(self, mock_loop, mock_from_url):
        mock_loop.return_value = loop = MagicMock()
        loop_id = id(loop)
        mock_redis = MagicMock()
        mock_from_url.return_value = mock_redis

        from broker import _pools, get_redis

        _pools.clear()
        _pools[loop_id] = existing = MagicMock()
        result = get_redis()
        assert result == existing
        mock_from_url.assert_not_called()

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_publish_run_message(self, mock_get_redis):
        from broker import publish_run_message

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        msg = {"type": "text", "content": "hello"}
        await publish_run_message("run-123", msg)

        mock_redis.publish.assert_awaited_once_with(
            "run:run-123", json.dumps(msg, ensure_ascii=False)
        )

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_close_redis(self, mock_get_redis):
        from broker import close_redis

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        from broker import _pools

        _pools.clear()
        loop = MagicMock()
        _pools[loop] = mock_redis

        with patch("broker.asyncio.get_running_loop", return_value=loop):
            await close_redis()
            mock_redis.aclose.assert_awaited_once()
            assert loop not in _pools


# ─────────────────────────────────────────────────────────────────────
# 3. backend/auth_jwt.py — JWT creation & verification
# ─────────────────────────────────────────────────────────────────────


"""Extended tests for backend/broker.py — Redis connection, message formatting, buffer."""

import asyncio
from unittest.mock import patch

import pytest


class TestBrokerFull:
    def test_broker_url_default_value(self):
        from broker import BROKER_URL
        assert BROKER_URL == "redis://localhost:6380/0"

    def test_result_backend_default_value(self):
        from broker import RESULT_BACKEND
        assert RESULT_BACKEND == "redis://localhost:6380/0"

    def test_channel_prefix(self):
        from broker import CHANNEL_PREFIX
        assert CHANNEL_PREFIX == "run:"

    def test_channel_format(self):
        from broker import _channel
        assert _channel("abc-123") == "run:abc-123"
        assert _channel("") == "run:"

    @patch("core.infra.redis_sentinel.AsyncRedis.from_url")
    @patch("broker.asyncio.get_running_loop")
    def test_get_redis_uses_correct_url(self, mock_loop, mock_from_url, monkeypatch):
        from broker import _pools, get_redis

        monkeypatch.setenv("REDIS_URL", "redis://custom-host:7777/5")
        monkeypatch.setenv("REDIS_POOL_SIZE", "20")
        mock_loop.return_value = MagicMock()
        mock_redis = MagicMock()
        mock_from_url.return_value = mock_redis
        _pools.clear()

        result = get_redis()
        mock_from_url.assert_called_once_with(
            "redis://custom-host:7777/5",
            max_connections=20,
            decode_responses=True,
            socket_keepalive=True,
            socket_connect_timeout=10,
            socket_timeout=10,
            health_check_interval=30,
            retry_on_timeout=True,
        )
        assert result == mock_redis

    @patch("core.infra.redis_sentinel.AsyncRedis.from_url")
    @patch("broker.asyncio.get_running_loop")
    def test_get_redis_creates_pool_on_new_loop(self, mock_loop, mock_from_url):
        from broker import _pools, get_redis

        loop1 = MagicMock()
        loop2 = MagicMock()
        redis1 = MagicMock()
        redis2 = MagicMock()
        mock_from_url.side_effect = [redis1, redis2]
        _pools.clear()

        mock_loop.return_value = loop1
        pool1 = get_redis()

        mock_loop.return_value = loop2
        pool2 = get_redis()

        assert pool1 is redis1
        assert pool2 is redis2
        assert pool1 is not pool2
        assert mock_from_url.call_count == 2

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_publish_run_message_structure(self, mock_get_redis):
        from broker import publish_run_message

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        msg = {"type": "test", "content": "hello"}
        await publish_run_message("run-xyz", msg)

        mock_redis.publish.assert_awaited_once_with(
            "run:run-xyz",
            json.dumps(msg, ensure_ascii=False),
        )

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_publish_run_message_with_chinese(self, mock_get_redis):
        from broker import publish_run_message

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        msg = {"type": "stream", "content": "你好世界"}
        await publish_run_message("run-cn", msg)

        mock_redis.publish.assert_awaited_once()
        published = json.loads(mock_redis.publish.call_args[0][1])
        assert published["content"] == "你好世界"

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_publish_run_message_empty_content(self, mock_get_redis):
        from broker import publish_run_message

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        await publish_run_message("run-empty", {"content": ""})
        mock_redis.publish.assert_awaited_once()

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_close_redis_removes_pool(self, mock_get_redis):
        from broker import _pools, close_redis

        loop = MagicMock()
        mock_pool = AsyncMock()
        _pools[loop] = mock_pool

        with patch("broker.asyncio.get_running_loop", return_value=loop):
            await close_redis()
            assert loop not in _pools
            mock_pool.aclose.assert_awaited_once()

    def test_celery_app_config(self):
        from broker import celery_app

        assert celery_app.main == "backend"
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.task_track_started is True
        assert celery_app.conf.task_acks_late is True

    def test_drain_buffer(self):
        from broker import _buffers, drain_buffer

        _buffers["run-buf"] = [{"type": "test"}]
        result = drain_buffer("run-buf")
        assert result == [{"type": "test"}]
        assert "run-buf" not in _buffers

    def test_drain_buffer_non_existent(self):
        from broker import drain_buffer

        result = drain_buffer("non-existent")
        assert result == []

    @pytest.mark.asyncio
    async def test_stop_buffer_cancels_task(self):

        from broker import _buffer_tasks, stop_buffer

        async def cancelled_coro():
            raise asyncio.CancelledError()

        real_task = asyncio.create_task(cancelled_coro())
        _buffer_tasks["run-stop"] = real_task

        await stop_buffer("run-stop")
        assert "run-stop" not in _buffer_tasks

    def test_channel_with_special_chars(self):
        from broker import _channel

        assert _channel("run-123_abc") == "run:run-123_abc"
        assert _channel("run/test") == "run:run/test"

    @patch("core.infra.redis_sentinel.AsyncRedis.from_url")
    @patch("broker.asyncio.get_running_loop")
    def test_get_redis_raises_on_no_loop(self, mock_loop, mock_from_url):
        from broker import _pools, get_redis

        mock_loop.side_effect = RuntimeError("No loop")
        _pools.clear()
        with pytest.raises(RuntimeError):
            get_redis()

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_publish_run_message_with_thinking_type(self, mock_get_redis):
        from broker import publish_run_message

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        msg = {"type": "thinking_stream", "agent_name": "Agent", "content": "思考中"}
        await publish_run_message("run-think", msg)

        mock_redis.publish.assert_awaited_once()
        published = json.loads(mock_redis.publish.call_args[0][1])
        assert published["type"] == "thinking_stream"
        assert published["content"] == "思考中"

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_publish_run_message_balance_warning(self, mock_get_redis):
        from broker import publish_run_message

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        msg = {"type": "balance_warning", "agent_name": "System", "content": "余额不足"}
        await publish_run_message("run-bal", msg)

        mock_redis.publish.assert_awaited_once()
        published = json.loads(mock_redis.publish.call_args[0][1])
        assert published["type"] == "balance_warning"

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_publish_run_message_tool_complete(self, mock_get_redis):
        from broker import publish_run_message

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        msg = {"type": "tool_complete", "agent_name": "Agent", "node": {}}
        await publish_run_message("run-tc", msg)

        mock_redis.publish.assert_awaited_once()
        published = json.loads(mock_redis.publish.call_args[0][1])
        assert published["type"] == "tool_complete"

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_publish_run_message_client_action(self, mock_get_redis):
        from broker import publish_run_message

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        msg = {"type": "client_action", "agent_name": "Agent", "action": {"type": "click"}}
        await publish_run_message("run-ca", msg)

        published = json.loads(mock_redis.publish.call_args[0][1])
        assert published["type"] == "client_action"
        assert published["action"] == {"type": "click"}

    def _blocking_get_message(self, calls: list, responses: list | None = None):
        """Return a get_message mock that records kwargs then blocks forever.

        Blocking (rather than returning immediately) is essential: an
        instantly-returning mock makes the worker's asyncio.wait_for resolve
        immediately and the worker busy-spins, starving the event loop.
        """
        responses = responses or []

        async def fake(*args, **kwargs):
            calls.append(kwargs)
            if responses:
                return responses.pop(0)
            await asyncio.Event().wait()

        return fake

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_buffer_run_messages_starts_task(self, mock_get_redis):

        from broker import _buffer_tasks, _buffers, buffer_run_messages

        mock_redis = MagicMock()
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        calls = []
        mock_pubsub.get_message = AsyncMock(side_effect=self._blocking_get_message(calls))
        mock_redis.pubsub.return_value = mock_pubsub
        mock_get_redis.return_value = mock_redis

        _buffers.clear()
        _buffer_tasks.clear()

        await buffer_run_messages("run-buf-task")
        assert "run-buf-task" in _buffer_tasks
        assert "run-buf-task" in _buffers
        mock_pubsub.subscribe.assert_awaited_once_with("run:run-buf-task")

        from broker import stop_buffer
        await stop_buffer("run-buf-task")

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_buffer_worker_uses_blocking_get_message(self, mock_get_redis):
        """Regression: worker must call get_message in BLOCKING mode.

        get_message() defaults to timeout=0 (non-blocking). Without timeout=None
        the outer wait_for never fires and the worker busy-spins ~100k iter/sec,
        pegging a CPU core for the whole run. This test pins the blocking call
        signature so the busy-loop cannot regress.
        """
        from broker import _buffer_tasks, _buffers, buffer_run_messages, stop_buffer

        mock_redis = MagicMock()
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        calls = []
        mock_pubsub.get_message = AsyncMock(side_effect=self._blocking_get_message(calls))
        mock_redis.pubsub.return_value = mock_pubsub
        mock_get_redis.return_value = mock_redis

        _buffers.clear()
        _buffer_tasks.clear()

        await buffer_run_messages("run-blocking")
        await asyncio.sleep(0.05)
        await stop_buffer("run-blocking")

        assert calls, "worker never called get_message"
        kwargs = calls[0]
        assert kwargs.get("timeout") is None, (
            f"get_message must block (timeout=None); got timeout={kwargs.get('timeout')!r}. "
            "Without it the buffer worker busy-spins ~100k iter/sec and pegs a CPU core."
        )
        assert kwargs.get("ignore_subscribe_messages") is True

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_buffer_worker_buffers_messages(self, mock_get_redis):
        """The worker accumulates published messages into the run's buffer."""
        from broker import _buffer_tasks, _buffers, buffer_run_messages, stop_buffer

        payload = {"type": "stream", "content": "hi"}
        mock_redis = MagicMock()
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        calls = []
        mock_pubsub.get_message = AsyncMock(
            side_effect=self._blocking_get_message(
                calls, [{"type": "message", "data": json.dumps(payload)}]
            )
        )
        mock_redis.pubsub.return_value = mock_pubsub
        mock_get_redis.return_value = mock_redis

        _buffers.clear()
        _buffer_tasks.clear()

        await buffer_run_messages("run-buf-msg")
        await asyncio.sleep(0.05)
        buf = _buffers["run-buf-msg"]
        await stop_buffer("run-buf-msg")

        assert buf == [payload]


# ── Per-user cross-client event channel ─────────────────────────────────────


async def test_publish_user_event_publishes_to_user_channel(monkeypatch: MonkeyPatch) -> None:
    from broker import _user_channel, publish_user_event

    mock_redis = MagicMock()
    monkeypatch.setattr("broker.get_redis", lambda: mock_redis)
    event = {"type": "session.deleted", "session_id": "s1", "ts": 1}
    await publish_user_event("u1", event)
    mock_redis.publish.assert_called_once_with(
        _user_channel("u1"), json.dumps(event, ensure_ascii=False)
    )


async def test_publish_user_event_fails_open(monkeypatch: MonkeyPatch) -> None:
    from broker import publish_user_event

    def _boom() -> None:
        raise RuntimeError("redis down")

    monkeypatch.setattr("broker.get_redis", _boom)
    await publish_user_event("u1", {"type": "session.deleted"})  # must not raise


async def test_subscribe_user_events_yields_parsed_messages(monkeypatch: MonkeyPatch) -> None:
    import asyncio

    from broker import subscribe_user_events

    payload = {"type": "session.updated", "session_id": "s2", "ts": 2}
    msg_queue: list[dict[str, object]] = [
        {"type": "subscribe"},
        {"type": "message", "data": json.dumps(payload)},
    ]

    class FakePubSub:
        async def subscribe(self, *args: object) -> None:
            pass

        async def get_message(self, **kwargs: object) -> dict[str, object] | None:
            if msg_queue:
                return msg_queue.pop(0)
            raise asyncio.CancelledError()

        async def close(self) -> None:
            pass

    mock_redis = MagicMock()
    mock_redis.pubsub.return_value = FakePubSub()
    monkeypatch.setattr("broker.get_redis", lambda: mock_redis)

    received: list[dict[str, object]] = []
    async for ev in subscribe_user_events("u1"):
        received.append(ev)
        break
    assert received == [payload]


