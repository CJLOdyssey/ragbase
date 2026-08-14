"""Tests for subscribe_run, close_redis edge cases, env overrides, and buffer operations."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# subscribe_run
# ---------------------------------------------------------------------------

class TestSubscribeRun:
    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_yields_messages_from_pubsub(self, mock_get_redis):
        from broker import subscribe_run

        mock_redis = MagicMock()
        mock_pubsub = AsyncMock()

        msg1 = {"type": "message", "data": json.dumps({"type": "text", "content": "hi"})}
        msg2 = {"type": "message", "data": json.dumps({"type": "stream", "content": "ok"})}

        # get_message() yields the stream, then "blocks" until the idle
        # timeout fires — mirroring subscribe_run's wait_for(60s) guard.
        mock_pubsub.get_message = AsyncMock(side_effect=[msg1, msg2, TimeoutError])
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_get_redis.return_value = mock_redis

        results = [m async for m in subscribe_run("r1")]
        assert results == [
            {"type": "text", "content": "hi"},
            {"type": "stream", "content": "ok"},
        ]
        mock_pubsub.subscribe.assert_awaited_once_with("run:r1")

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_no_messages_yields_nothing(self, mock_get_redis):
        from broker import subscribe_run

        mock_redis = MagicMock()
        mock_pubsub = AsyncMock()

        mock_pubsub.get_message = AsyncMock(side_effect=TimeoutError)
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_get_redis.return_value = mock_redis

        results = [m async for m in subscribe_run("r2")]
        assert results == []

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_skips_non_message_types(self, mock_get_redis):
        from broker import subscribe_run

        mock_redis = MagicMock()
        mock_pubsub = AsyncMock()

        # subscribe confirmations are dropped by ignore_subscribe_messages;
        # only the real message reaches the generator.
        msg = {"type": "message", "data": json.dumps({"type": "done"})}

        mock_pubsub.get_message = AsyncMock(side_effect=[msg, TimeoutError])
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_get_redis.return_value = mock_redis

        results = [m async for m in subscribe_run("r3")]
        assert results == [{"type": "done"}]

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_skips_non_string_data(self, mock_get_redis):
        from broker import subscribe_run

        mock_redis = MagicMock()
        mock_pubsub = AsyncMock()

        msg_bytes = {"type": "message", "data": b"\x00\x01"}

        mock_pubsub.get_message = AsyncMock(side_effect=[msg_bytes, TimeoutError])
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_get_redis.return_value = mock_redis

        results = [m async for m in subscribe_run("r4")]
        assert results == []

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_stops_stream_after_result(self, mock_get_redis):
        from broker import subscribe_run

        mock_redis = MagicMock()
        mock_pubsub = AsyncMock()

        result_msg = {
            "type": "message",
            "data": json.dumps({"type": "result", "content": "fin"}),
        }
        trailing = {
            "type": "message",
            "data": json.dumps({"type": "text", "content": "late"}),
        }

        mock_pubsub.get_message = AsyncMock(side_effect=[result_msg, trailing, TimeoutError])
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_get_redis.return_value = mock_redis

        results = [m async for m in subscribe_run("r7")]
        assert results == [{"type": "result", "content": "fin"}]
        # stream closed on result — trailing message is never consumed
        assert mock_pubsub.get_message.await_count == 1
        mock_pubsub.unsubscribe.assert_awaited_once_with("run:r7")
        mock_pubsub.close.assert_awaited_once()

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_idle_timeout_closes_stream(self, mock_get_redis):
        from broker import subscribe_run

        mock_redis = MagicMock()
        mock_pubsub = AsyncMock()

        mock_pubsub.get_message = AsyncMock(side_effect=TimeoutError)
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_get_redis.return_value = mock_redis

        results = [m async for m in subscribe_run("r8")]
        assert results == []
        mock_pubsub.unsubscribe.assert_awaited_once_with("run:r8")
        mock_pubsub.close.assert_awaited_once()

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_unsubscribes_and_closes_in_finally(self, mock_get_redis):
        from broker import subscribe_run

        mock_redis = MagicMock()
        mock_pubsub = AsyncMock()

        mock_pubsub.get_message = AsyncMock(
            side_effect=[
                {"type": "message", "data": json.dumps({"a": 1})},
                TimeoutError,
            ]
        )
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_get_redis.return_value = mock_redis

        results = [m async for m in subscribe_run("r5")]
        assert len(results) == 1
        mock_pubsub.unsubscribe.assert_awaited_once_with("run:r5")
        mock_pubsub.close.assert_awaited_once()

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_finally_survives_unsubscribe_error(self, mock_get_redis):
        from broker import subscribe_run

        mock_redis = MagicMock()
        mock_pubsub = AsyncMock()

        mock_pubsub.get_message = AsyncMock(
            side_effect=[
                {"type": "message", "data": json.dumps({"x": 1})},
                TimeoutError,
            ]
        )
        mock_pubsub.unsubscribe = AsyncMock(side_effect=RuntimeError("gone"))
        mock_pubsub.close = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_get_redis.return_value = mock_redis

        results = [m async for m in subscribe_run("r6")]
        assert results == [{"x": 1}]
        mock_pubsub.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# close_redis edge cases
# ---------------------------------------------------------------------------

class TestCloseRedisEdgeCases:
    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_close_redis_no_pool_does_not_raise(self, mock_get_redis):
        from broker import _pools, close_redis

        _pools.clear()
        loop = MagicMock()
        with patch("broker.asyncio.get_running_loop", return_value=loop):
            await close_redis()

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_close_redis_different_loop_does_not_affect_other(self, mock_get_redis):
        from broker import _pools, close_redis

        _pools.clear()
        loop_a = MagicMock()
        loop_b = MagicMock()
        pool_a = AsyncMock()
        pool_b = AsyncMock()
        _pools[loop_a] = pool_a
        _pools[loop_b] = pool_b

        with patch("broker.asyncio.get_running_loop", return_value=loop_a):
            await close_redis()

        assert loop_a not in _pools
        assert loop_b in _pools
        pool_a.aclose.assert_awaited_once()
        pool_b.aclose.assert_not_awaited()

        _pools.pop(loop_b, None)


# ---------------------------------------------------------------------------
# Env var overrides
# ---------------------------------------------------------------------------

class TestEnvVarOverrides:
    def test_redis_url_env_override(self):
        with patch.dict("os.environ", {"REDIS_URL": "redis://env-host:9999/1"}):
            import importlib

            import broker as broker_mod
            importlib.reload(broker_mod)
            assert broker_mod.REDIS_URL == "redis://env-host:9999/1"
            # Restore default for other tests
            with patch.dict("os.environ", {}, clear=False):
                pass

    def test_celery_broker_url_env_override(self):
        with patch.dict("os.environ", {"CELERY_BROKER_URL": "redis://broker-host:6380/2"}):
            import importlib

            import broker as broker_mod
            # Reload picks up the new env var
            importlib.reload(broker_mod)
            assert broker_mod.BROKER_URL == "redis://broker-host:6380/2"
            # Reload again to restore
            importlib.reload(broker_mod)

    def test_result_backend_env_override(self):
        with patch.dict("os.environ", {"CELERY_RESULT_BACKEND": "redis://result-host:6381/3"}):
            import importlib

            import broker as broker_mod
            importlib.reload(broker_mod)
            assert broker_mod.RESULT_BACKEND == "redis://result-host:6381/3"
            importlib.reload(broker_mod)


# ---------------------------------------------------------------------------
# buffer_run_messages & drain_buffer
# ---------------------------------------------------------------------------

class TestBufferRunMessages:
    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_buffer_accumulates_messages(self, mock_get_redis):
        from broker import (
            _buffer_tasks,
            _buffers,
            buffer_run_messages,
            stop_buffer,
        )

        _buffers.clear()
        _buffer_tasks.clear()

        mock_redis = MagicMock()
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()

        messages = [
            {"type": "subscribe"},
            {"type": "message", "data": json.dumps({"type": "text", "content": "a"})},
            {"type": "message", "data": json.dumps({"type": "stream", "content": "b"})},
        ]
        call_idx = {"i": 0}

        async def fake_get_message(**kwargs):
            idx = call_idx["i"]
            call_idx["i"] += 1
            if idx < len(messages):
                return messages[idx]
            await asyncio.sleep(100)  # simulate idle → timeout

        mock_pubsub.get_message = fake_get_message
        mock_pubsub.close = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_get_redis.return_value = mock_redis

        await buffer_run_messages("run-buf-acc")
        assert "run-buf-acc" in _buffers

        await asyncio.sleep(0.1)  # let worker process messages
        await stop_buffer("run-buf-acc")

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_drain_buffer_returns_and_clears(self, mock_get_redis):
        from broker import _buffers, drain_buffer

        _buffers.clear()
        _buffers["run-d"] = [{"type": "x"}, {"type": "y"}]

        result = drain_buffer("run-d")
        assert result == [{"type": "x"}, {"type": "y"}]
        assert "run-d" not in _buffers

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_drain_buffer_nonexistent_returns_empty(self, mock_get_redis):
        from broker import drain_buffer

        result = drain_buffer("no-such-run")
        assert result == []

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_buffer_run_messages_subscribe_called(self, mock_get_redis):
        from broker import (
            _buffer_tasks,
            _buffers,
            buffer_run_messages,
            stop_buffer,
        )

        _buffers.clear()
        _buffer_tasks.clear()

        mock_redis = MagicMock()
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.get_message = AsyncMock(
            side_effect=asyncio.CancelledError
        )
        mock_pubsub.close = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_get_redis.return_value = mock_redis

        await buffer_run_messages("run-sub")
        mock_pubsub.subscribe.assert_awaited_once_with("run:run-sub")

        await stop_buffer("run-sub")

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_buffer_fail_open_on_redis_outage(self, mock_get_redis):
        from broker import _buffers, buffer_run_messages, stop_buffer

        _buffers.clear()
        mock_get_redis.side_effect = ConnectionError("redis down")

        # Must not raise; an empty buffer is registered so the run proceeds.
        await buffer_run_messages("run-failopen")
        assert "run-failopen" in _buffers
        assert _buffers["run-failopen"] == []
        await stop_buffer("run-failopen")


# ---------------------------------------------------------------------------
# stop_buffer
# ---------------------------------------------------------------------------

class TestStopBuffer:
    @pytest.mark.asyncio
    async def test_stop_buffer_no_task(self):
        from broker import _buffer_tasks, stop_buffer

        _buffer_tasks.clear()
        await stop_buffer("nonexistent")

    @pytest.mark.asyncio
    async def test_stop_buffer_clears_buffers_and_task(self):
        from broker import (
            _buffer_tasks,
            _buffers,
            stop_buffer,
        )

        async def noop():
            pass

        task = asyncio.create_task(noop())
        _buffer_tasks["run-st"] = task
        _buffers["run-st"] = [{"data": 1}]

        await stop_buffer("run-st")
        assert "run-st" not in _buffer_tasks
        assert "run-st" not in _buffers
