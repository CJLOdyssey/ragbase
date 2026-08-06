"""Logging handler that persists log records as observability events."""

import logging
import time
import traceback

from observability.schema import Event
from observability.store import get_store
from observability.trace import current_trace_id


class ObservabilityHandler(logging.Handler):
    """Logging handler that writes records to the event store."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            evt = Event(
                trace_id=current_trace_id(),
                level=record.levelname,
                message=record.getMessage(),
                logger=record.name,
                timestamp=time.time(),
                span_id="",
                error_type=self._error_type(record),
                error_stack=self._stack(record),
                event_type="log",
            )
            get_store().write(evt)
        except Exception:
            pass

    def _error_type(self, record: logging.LogRecord) -> str | None:
        if record.exc_info and record.exc_info[0]:
            return record.exc_info[0].__name__
        return None

    def _stack(self, record: logging.LogRecord) -> str | None:
        if not record.exc_info:
            return None
        return "".join(traceback.format_exception(*record.exc_info))
