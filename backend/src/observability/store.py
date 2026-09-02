"""EventStore — writes and queries observability events to SQLite.

High cohesion: single responsibility — persist and retrieve events.
Low coupling: callers pass Event objects, never touch SQL.
"""

import logging
import os
import queue
import shutil
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from observability.schema import SCHEMA_SQL, Event

_logger = logging.getLogger(__name__)

_DB_PATH = os.environ.get("OBSERVABILITY_DB", str(Path(__file__).parent / "events.db"))

# Minimum free disk space in bytes before writes are rejected.
_DISK_MIN_FREE = int(os.environ.get("OBSERVABILITY_MIN_DISK_MB", "100")) * 1024 * 1024


_INSERT_SQL = """INSERT INTO events
   (timestamp,trace_id,span_id,parent_span_id,level,logger,
    message,error_type,error_stack,duration_ms,tags,event_type)
   VALUES (:timestamp,:trace_id,:span_id,:parent_span_id,:level,:logger,
           :message,:error_type,:error_stack,:duration_ms,:tags,:event_type)"""


class EventStore:
    """Thread-safe, non-blocking event store backed by SQLite (WAL mode).

    Writes are offloaded to a background thread via a queue so the caller
    (including sync logging handlers) never blocks on I/O.
    """

    def __init__(self, db_path: str = _DB_PATH) -> None:
        self._db_path = db_path
        self._queue: queue.SimpleQueue[dict[str, Any]] = queue.SimpleQueue()
        self._closed = False
        self._write_errors: int = 0
        self._disk_errors: int = 0
        self._last_heartbeat: float = 0.0

        conn = sqlite3.connect(db_path, timeout=5)
        conn.executescript(SCHEMA_SQL)
        conn.close()

        self._writer = threading.Thread(target=self._writer_loop, daemon=True)
        self._writer.start()

    def _disk_free(self) -> float:
        """Return free disk space in bytes, or -1 on failure."""
        try:
            usage = shutil.disk_usage(self._db_path)
            return usage.free
        except OSError:
            return -1.0

    def write(self, event: Event) -> None:
        """Enqueue an event for background persistence."""
        if self._closed:
            self._write_errors += 1
            return
        free = self._disk_free()
        if 0 < free < _DISK_MIN_FREE:
            self._disk_errors += 1
            return
        try:
            self._queue.put(event.to_row(), block=False)
            self._last_heartbeat = time.time()
        except queue.Full:
            self._write_errors += 1

    def self_check(self) -> dict[str, Any]:
        """Return internal health metrics (queue size, errors, disk, writer status)."""
        free = self._disk_free()
        return {
            "queue_size": _writer_size(self._queue),
            "write_errors": self._write_errors,
            "disk_errors": self._disk_errors,
            "disk_free_mb": round(free / (1024 * 1024), 1) if free > 0 else free,
            "disk_min_free_mb": _DISK_MIN_FREE // (1024 * 1024),
            "writer_alive": self._writer.is_alive(),
            "closed": self._closed,
            "last_heartbeat": self._last_heartbeat,
            "db_path": self._db_path,
        }

    def _query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        """Run a read-only query and return results as dicts."""
        conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def recent(self, seconds: int = 300, limit: int = 50) -> list[dict[str, Any]]:
        """Return events within the last ``seconds``, newest first."""
        cutoff = time.time() - seconds
        return self._query(
            "SELECT * FROM events WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT ?",
            (cutoff, limit),
        )

    def count(self) -> int:
        """Total number of persisted events."""
        row = self._query("SELECT COUNT(*) AS cnt FROM events")[0]
        return int(row["cnt"])

    def by_trace(self, trace_id: str, limit: int = 200) -> list[dict[str, Any]]:
        """Return all events for a given trace ID."""
        return self._query(
            "SELECT * FROM events WHERE trace_id=? ORDER BY timestamp ASC LIMIT ?",
            (trace_id, limit),
        )

    def recent_errors(self, seconds: int = 300, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent events that have a non-empty error_type."""
        cutoff = time.time() - seconds
        return self._query(
            """SELECT * FROM events
               WHERE timestamp >= ? AND error_type != ''
               ORDER BY timestamp DESC LIMIT ?""",
            (cutoff, limit),
        )

    def slow_events(self, min_ms: float = 1000, seconds: int = 3600, limit: int = 50) -> list[dict[str, Any]]:
        """Return events exceeding a minimum duration threshold."""
        cutoff = time.time() - seconds
        return self._query(
            """SELECT * FROM events
               WHERE timestamp >= ? AND duration_ms >= ?
               ORDER BY duration_ms DESC LIMIT ?""",
            (cutoff, min_ms, limit),
        )

    def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """Full-text search across message, error_type, logger, and trace_id."""
        like = f"%{query}%"
        return self._query(
            """SELECT * FROM events
               WHERE message LIKE ? OR error_type LIKE ? OR logger LIKE ? OR trace_id LIKE ?
               ORDER BY timestamp DESC LIMIT ?""",
            (like, like, like, like, limit),
        )

    def stats(self, seconds: int = 300) -> dict[str, Any]:
        """Return per-level event counts and error total within the time window."""
        cutoff = time.time() - seconds
        data = self._query(
            """SELECT level, COUNT(*) as cnt
               FROM events WHERE timestamp >= ?
               GROUP BY level""",
            (cutoff,),
        )
        by_level = {r["level"]: r["cnt"] for r in data}
        error_count = self._query(
            "SELECT COUNT(*) as cnt FROM events WHERE timestamp >= ? AND error_type != ''",
            (cutoff,),
        )[0]["cnt"]
        return {"window_seconds": seconds, "by_level": by_level, "errors": error_count}

    def error_trace_ids(self, seconds: int = 300, limit: int = 20) -> list[dict[str, Any]]:
        """Return distinct trace IDs that have errors in the time window."""
        cutoff = time.time() - seconds
        return self._query(
            """SELECT trace_id, error_type, message, timestamp
               FROM events
               WHERE timestamp >= ? AND error_type != ''
               GROUP BY trace_id
               ORDER BY MAX(timestamp) DESC
               LIMIT ?""",
            (cutoff, limit),
        )

    def close(self) -> None:
        """Mark the store as closed, rejecting future writes."""
        self._closed = True

    def cleanup(self, retention_days: int = 30) -> int:
        """Delete events older than `retention_days` and return the row count.

        Runs inline (not through the background writer queue) so it never
        contends for queue slots with live writes. Returns -1 on failure.
        """
        if retention_days <= 0:
            return 0
        cutoff = time.time() - retention_days * 86400
        try:
            conn = sqlite3.connect(self._db_path, timeout=10)
            conn.execute("PRAGMA synchronous=NORMAL")
            try:
                cursor = conn.execute(
                    "DELETE FROM events WHERE timestamp < ?", (cutoff,)
                )
                deleted = cursor.rowcount
                conn.commit()
                return deleted
            finally:
                conn.close()
        except Exception:
            return -1


    def _writer_loop(self) -> None:
        """Background thread that drains the queue and batch-inserts into SQLite.

        Must survive transient DB faults: a failed batch is dropped and
        counted in ``write_errors`` (events are best-effort diagnostics).
        Letting an exception escape would kill this thread silently and
        every later write would pile up in memory forever.
        """
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.execute("PRAGMA synchronous=NORMAL")
        try:
            while True:
                rows = [self._queue.get()]
                while not self._queue.empty() and len(rows) < 100:
                    rows.append(self._queue.get_nowait())
                try:
                    conn.executemany(_INSERT_SQL, rows)
                    conn.commit()
                except Exception:
                    self._write_errors += 1
                    _logger.warning(
                        "observability writer dropped %d rows", len(rows), exc_info=True
                    )
                    time.sleep(0.5)  # avoid hot-spinning on a persistent fault
        finally:
            conn.close()


def _writer_size(q: "queue.SimpleQueue[dict[str, Any]]") -> int:
    """Return the current queue size."""
    return q.qsize()


# Module-level singleton — created on first use.
_store: EventStore | None = None
_store_lock = threading.Lock()


def get_store() -> EventStore:
    """Return the module-level EventStore singleton (thread-safe creation)."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = EventStore()
    return _store
