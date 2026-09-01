"""Lightweight async event bus for application-level decoupling.

Usage
-----
    from core.infra.events import bus, Events

    async def on_run_created(run_id: str, **kw):
        notify(run_id)

    bus.on(Events.RUN_CREATED, on_run_created)

    # elsewhere …
    await bus.emit(Events.RUN_CREATED, run_id="abc-123")
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

EventHandler = Callable[..., Any]


class EventBus:
    """Simple pub/sub event bus for decoupling application modules."""

    def __init__(self) -> None:
        """Initialize the event bus."""
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def on(self, event: str, handler: EventHandler) -> EventHandler:
        """Subscribe a handler to an event.  Can be used as a decorator."""
        self._handlers[event].append(handler)
        return handler

    def off(self, event: str, handler: EventHandler) -> None:
        """Unsubscribe a handler from an event."""
        self._handlers[event] = [h for h in self._handlers[event] if h is not handler]
        if not self._handlers[event]:
            del self._handlers[event]

    async def emit(self, event: str, **data: Any) -> None:
        """Emit an event, calling all registered handlers with ``**data``."""
        for handler in self._handlers.get(event, []):
            try:
                # Call first, then await if needed — this also covers handlers
                # wrapped in functools.partial, which iscoroutinefunction misses.
                result = handler(**data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                name = getattr(handler, "__name__", repr(handler))
                logger.exception("Event handler %r failed for %s", name, event)

    def clear(self) -> None:
        """Remove all handlers (useful in tests)."""
        self._handlers.clear()


bus = EventBus()


class Events:
    """Canonical event names used across the application."""

    RUN_CREATED = "run:created"
    AGENT_CONFIG_CHANGED = "agent_config:changed"
    KEY_CREATED = "key:created"
    KEY_DELETED = "key:deleted"
