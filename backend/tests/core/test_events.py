"""Tests for the async event bus (backend/core/infra/events.py)."""

import asyncio

import pytest
from core.infra.events import EventBus, Events, bus


class TestEventBus:
    def setup_method(self):
        self.bus = EventBus()

    def test_on_subscribes_handler(self):
        results = []

        def handler(x):
            results.append(x)

        ret = self.bus.on("test", handler)
        assert ret is handler
        assert handler in self.bus._handlers["test"]

    def test_off_unsubscribes_handler(self):
        def handler(x):
            pass

        self.bus.on("test", handler)
        self.bus.off("test", handler)
        assert handler not in self.bus._handlers.get("test", [])

    def test_emit_sync_handler(self):
        results = []

        def handler(x):
            results.append(x)

        self.bus.on("test", handler)
        asyncio.run(self.bus.emit("test", x=42))
        assert results == [42]

    @pytest.mark.asyncio
    async def test_emit_async_handler(self):
        results = []

        async def handler(x):
            results.append(x)

        self.bus.on("test", handler)
        await self.bus.emit("test", x="hello")
        assert results == ["hello"]

    @pytest.mark.asyncio
    async def test_emit_handler_exception_is_caught(self):
        def handler(x):
            raise ValueError("oops")

        self.bus.on("test", handler)
        await self.bus.emit("test", x=1)

    def test_clear_removes_all_handlers(self):
        def h(x):
            pass

        self.bus.on("a", h)
        self.bus.on("b", h)
        self.bus.clear()
        assert self.bus._handlers == {}


class TestEventsConstants:
    def test_run_created(self):
        assert Events.RUN_CREATED == "run:created"


def test_global_bus_exists():
    assert bus is not None
