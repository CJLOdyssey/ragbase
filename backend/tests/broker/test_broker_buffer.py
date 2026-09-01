"""Tests for broker buffer operations (buffer_run_messages / drain_buffer / stop_buffer)
and the per-user event channel (publish/subscribe_user_events)."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestBufferRunMessages:
    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_buffer_worker_blocks_on_get_message(self, mock_get_redis):
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

        async def _blocking_get_message(**kwargs):
            calls.append(kwargs)
            await asyncio.Event().wait()

        mock_pubsub.get_message = AsyncMock(side_effect=_blocking_get_message)
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

        async def _get_message(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return {"type": "message", "data": json.dumps(payload)}
            await asyncio.Event().wait()

        mock_pubsub.get_message = AsyncMock(side_effect=_get_message)
        mock_redis.pubsub.return_value = mock_pubsub
        mock_get_redis.return_value = mock_redis

        _buffers.clear()
        _buffer_tasks.clear()

        await buffer_run_messages("run-buf-msg")
        await asyncio.sleep(0.05)
        buf = _buffers["run-buf-msg"]
        await stop_buffer("run-buf-msg")

        assert buf == [payload]

    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_buffer_run_messages_starts_task_and_subscribes(self, mock_get_redis):
        from broker import _buffer_tasks, _buffers, buffer_run_messages, stop_buffer

        mock_redis = MagicMock()
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.get_message = AsyncMock(side_effect=asyncio.CancelledError)
        mock_pubsub.close = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_get_redis.return_value = mock_redis

        _buffers.clear()
        _buffer_tasks.clear()

        await buffer_run_messages("run-buf-task")
        assert "run-buf-task" in _buffer_tasks
        assert "run-buf-task" in _buffers
        mock_pubsub.subscribe.assert_awaited_once_with("run:run-buf-task")

        await stop_buffer("run-buf-task")

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
            # 非 str data（如二进制）必须跳过，不进入 buffer
            {"type": "message", "data": b"\x00\x01"},
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


class TestSubscribeUserEvents:
    @patch("broker.get_redis")
    @pytest.mark.asyncio
    async def test_skips_non_json_messages(self, mock_get_redis):
        """非 JSON data 跳过（不 yield 不 raise），流保持存活。"""
        from broker import subscribe_user_events

        mock_redis = MagicMock()
        mock_pubsub = AsyncMock()
        mock_pubsub.get_message = AsyncMock(
            side_effect=[
                {"type": "message", "data": "not-json"},
                {"type": "message", "data": "also-bad"},
                asyncio.CancelledError(),
            ]
        )
        mock_pubsub.close = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_get_redis.return_value = mock_redis

        results = []
        try:
            async for m in subscribe_user_events("u1"):
                results.append(m)
        except asyncio.CancelledError:
            pass

        assert results == []
        mock_pubsub.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_publish_user_event_uses_user_channel(self, monkeypatch):
        from broker import _user_channel, publish_user_event

        mock_redis = MagicMock()
        monkeypatch.setattr("broker.get_redis", lambda: mock_redis)
        event = {"type": "session.deleted", "session_id": "s1", "ts": 1}
        await publish_user_event("u1", event)
        mock_redis.publish.assert_called_once_with(
            _user_channel("u1"), json.dumps(event, ensure_ascii=False)
        )

    @pytest.mark.asyncio
    async def test_publish_user_event_fails_open(self, monkeypatch):
        """Redis 故障时发布事件不抛异常（fail-open）。"""
        from broker import publish_user_event

        def _boom() -> None:
            raise RuntimeError("redis down")

        monkeypatch.setattr("broker.get_redis", _boom)
        await publish_user_event("u1", {"type": "session.deleted"})  # must not raise

    @pytest.mark.asyncio
    async def test_subscribe_user_events_yields_parsed_messages(self, monkeypatch):
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
