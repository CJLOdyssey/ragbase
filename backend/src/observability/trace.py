"""Distributed tracing primitives using contextvars for async-safe span tracking."""

import contextvars
import time
import uuid
from contextlib import contextmanager
from typing import Any

from observability.schema import Event
from observability.store import get_store

_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
_span_id: contextvars.ContextVar[str] = contextvars.ContextVar("span_id", default="")
_depth: contextvars.ContextVar[int] = contextvars.ContextVar("depth", default=0)


def current_trace_id() -> str:
    """Get the current trace ID from context."""
    return _trace_id.get()


def current_span_id() -> str:
    """Get the current span ID from context."""
    return _span_id.get()


def set_trace_id(tid: str) -> None:
    """Set the trace ID for the current context."""
    _trace_id.set(tid)


def _make_id() -> str:
    return uuid.uuid4().hex[:12]


@contextmanager
def span(
    name: str,
    logger_name: str = "",
    tags: dict[str, Any] | None = None,
) -> Any:
    """Create a traced span context that records timing and errors."""
    tid = _trace_id.get()
    if not tid:
        tid = _make_id()
        _trace_id.set(tid)

    parent_sid = _span_id.get()
    sid = _make_id()
    _span_id.set(sid)
    depth = _depth.get()
    _depth.set(depth + 1)

    t0 = time.time()
    error_type = None
    error_stack = None
    try:
        yield
    except BaseException as exc:
        error_type = type(exc).__name__
        error_stack = _format_exc(exc)
        raise
    finally:
        elapsed = (time.time() - t0) * 1000
        _depth.set(depth)
        _span_id.set(parent_sid)

        evt = Event(
            trace_id=tid,
            span_id=sid,
            parent_span_id=parent_sid,
            level="ERROR" if error_type else "INFO",
            message=name,
            logger=logger_name or "trace",
            timestamp=t0,
            duration_ms=elapsed,
            error_type=error_type,
            error_stack=error_stack,
            tags=tags or {},
            event_type="span",
        )
        get_store().write(evt)


def _format_exc(exc: BaseException) -> str:
    import traceback
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
