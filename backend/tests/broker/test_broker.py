"""Unit tests for backend/broker.py (Redis URL parsing, pub/sub, buffers)."""

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

    def real_get_redis():
        loop = mod_broker.asyncio.get_running_loop()
        loop_id = id(loop)
        pool = mod_broker._pools.get(loop_id)
        if pool is None:
            pool = _original_create_redis()
            mod_broker._pools[loop_id] = pool
        return pool

    monkeypatch.setattr("broker.get_redis", real_get_redis)
    monkeypatch.setattr(
        "core.infra.redis_sentinel.create_redis", _original_create_redis
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

    def test_result_backend_default(self):
        from broker import RESULT_BACKEND

        assert RESULT_BACKEND == "redis://localhost:6380/0"

    def test_channel_prefix(self):
        from broker import CHANNEL_PREFIX

        assert CHANNEL_PREFIX == "run:"

    def test_channel_format(self):
        from broker import _channel

        assert _channel("run-abc") == "run:run-abc"
        assert _channel("") == "run:"
        assert _channel("run-123_abc") == "run:run-123_abc"
        assert _channel("run/test") == "run:run/test"

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
    def test_get_redis_uses_custom_url(self, mock_loop, mock_from_url, monkeypatch):
        monkeypatch.setenv("REDIS_URL", "redis://custom-host:7777/5")
        monkeypatch.setenv("REDIS_POOL_SIZE", "20")
        mock_loop.return_value = MagicMock()
        mock_redis = MagicMock()
        mock_from_url.return_value = mock_redis

        from broker import _pools, get_redis

        _pools.clear()

        get_redis()
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

    @patch("core.infra.redis_sentinel.AsyncRedis.from_url")
    @patch("broker.asyncio.get_running_loop")
    def test_get_redis_creates_pool_per_loop(self, mock_loop, mock_from_url):
        from broker import _pools, get_redis

        redis1 = MagicMock()
        redis2 = MagicMock()
        mock_from_url.side_effect = [redis1, redis2]
        _pools.clear()

        mock_loop.return_value = MagicMock()
        pool1 = get_redis()

        mock_loop.return_value = MagicMock()
        pool2 = get_redis()

        assert pool1 is redis1
        assert pool2 is redis2
        assert pool1 is not pool2
        assert mock_from_url.call_count == 2

    @patch("core.infra.redis_sentinel.AsyncRedis.from_url")
    @patch("broker.asyncio.get_running_loop")
    def test_get_redis_raises_without_loop(self, mock_loop, mock_from_url):
        from broker import _pools, get_redis

        mock_loop.side_effect = RuntimeError("No running loop")
        _pools.clear()
        with pytest.raises(RuntimeError):
            get_redis()


class TestPublishRunMessage:
    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_publishes_json_payload(self, mock_get_redis):
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
    async def test_preserves_unicode_content(self, mock_get_redis):
        from broker import publish_run_message

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        msg = {"type": "thinking_stream", "agent_name": "Agent", "content": "思考中"}
        await publish_run_message("run-cn", msg)

        published = json.loads(mock_redis.publish.call_args[0][1])
        assert published["content"] == "思考中"

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_publishes_structured_message_types(self, mock_get_redis):
        """balance_warning / tool_complete / client_action 等结构消息原样透传。"""
        from broker import publish_run_message

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        cases = [
            {"type": "balance_warning", "agent_name": "System", "content": "余额不足"},
            {"type": "tool_complete", "agent_name": "Agent", "node": {}},
            {"type": "client_action", "agent_name": "Agent", "action": {"type": "click"}},
        ]
        for msg in cases:
            await publish_run_message("run-x", msg)
            published = json.loads(mock_redis.publish.call_args[0][1])
            assert published == msg


class TestCloseRedis:
    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_closes_pool_and_removes_from_registry(self, mock_get_redis):
        from broker import _pools, close_redis

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        loop = MagicMock()
        _pools[loop] = mock_redis

        with patch("broker.asyncio.get_running_loop", return_value=loop):
            await close_redis()
            mock_redis.aclose.assert_awaited_once()
            assert loop not in _pools

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_close_redis_without_pool_is_noop(self, mock_get_redis):
        from broker import _pools, close_redis

        _pools.clear()
        loop = MagicMock()
        with patch("broker.asyncio.get_running_loop", return_value=loop):
            await close_redis()


class TestCeleryConfig:
    def test_celery_app_config(self):
        from broker import celery_app

        assert celery_app.main == "backend"
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.task_track_started is True
        assert celery_app.conf.task_acks_late is True


class TestBufferOps:
    def test_drain_buffer_returns_and_clears(self):
        from broker import _buffers, drain_buffer

        _buffers["run-buf"] = [{"type": "test"}]
        result = drain_buffer("run-buf")
        assert result == [{"type": "test"}]
        assert "run-buf" not in _buffers

    def test_drain_buffer_nonexistent_returns_empty(self):
        from broker import drain_buffer

        assert drain_buffer("non-existent") == []

    @pytest.mark.asyncio
    async def test_stop_buffer_cancels_task(self):
        import asyncio

        from broker import _buffer_tasks, stop_buffer

        async def cancelled_coro():
            raise asyncio.CancelledError()

        real_task = asyncio.create_task(cancelled_coro())
        _buffer_tasks["run-stop"] = real_task

        await stop_buffer("run-stop")
        assert "run-stop" not in _buffer_tasks
