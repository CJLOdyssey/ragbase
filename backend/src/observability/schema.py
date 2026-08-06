"""Data models and SQL schema for the observability event store."""

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Event:
    """A single observability event — log, span, or error."""

    trace_id: str
    level: str
    message: str
    logger: str
    timestamp: float  # time.time()
    span_id: str = ""
    parent_span_id: str | None = None
    error_type: str | None = None
    error_stack: str | None = None
    duration_ms: float | None = None
    tags: dict[str, Any] = field(default_factory=dict)
    event_type: str = "log"  # log | span | error

    def to_row(self) -> dict[str, Any]:
        """Serialize this event into a dict for SQLite insertion."""
        return {
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id or "",
            "level": self.level,
            "logger": self.logger,
            "message": self.message,
            "error_type": self.error_type or "",
            "error_stack": self.error_stack or "",
            "duration_ms": self.duration_ms or 0,
            "tags": json.dumps(self.tags, ensure_ascii=False),
            "event_type": self.event_type,
        }


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    trace_id TEXT NOT NULL,
    span_id TEXT NOT NULL DEFAULT '',
    parent_span_id TEXT NOT NULL DEFAULT '',
    level TEXT NOT NULL,
    logger TEXT NOT NULL,
    message TEXT NOT NULL,
    error_type TEXT NOT NULL DEFAULT '',
    error_stack TEXT NOT NULL DEFAULT '',
    duration_ms REAL NOT NULL DEFAULT 0,
    tags TEXT NOT NULL DEFAULT '{}',
    event_type TEXT NOT NULL DEFAULT 'log'
);

CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_trace ON events(trace_id);
CREATE INDEX IF NOT EXISTS idx_events_level ON events(level);
CREATE INDEX IF NOT EXISTS idx_events_error ON events(error_type) WHERE error_type != '';
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_duration ON events(duration_ms) WHERE duration_ms > 0;
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
"""
