"""Tests for backend/observability/ — EventStore, Event schema, handler."""

import json
import logging
import os
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.requirement("REQ-OBS-001")
class TestEventSchema:
    def test_create_event(self):
        from observability.schema import Event

        evt = Event(
            trace_id="trace-1",
            level="INFO",
            message="test message",
            logger="test",
            timestamp=1234567890.0,
        )
        assert evt.trace_id == "trace-1"
        assert evt.level == "INFO"
        assert evt.event_type == "log"
        assert evt.span_id == ""
        assert evt.parent_span_id is None

    def test_event_to_row(self):
        from observability.schema import Event

        evt = Event(
            trace_id="t1",
            level="ERROR",
            message="error occurred",
            logger="app",
            timestamp=1000.0,
            error_type="ValueError",
            error_stack="Traceback...",
            duration_ms=500.0,
            tags={"key": "val"},
            event_type="error",
        )
        row = evt.to_row()
        assert row["trace_id"] == "t1"
        assert row["level"] == "ERROR"
        assert row["error_type"] == "ValueError"
        assert row["duration_ms"] == 500.0
        assert json.loads(row["tags"]) == {"key": "val"}
        assert row["event_type"] == "error"

    def test_event_to_row_defaults(self):
        from observability.schema import Event

        evt = Event(trace_id="t2", level="INFO", message="msg", logger="log", timestamp=2000.0)
        row = evt.to_row()
        assert row["span_id"] == ""
        assert row["parent_span_id"] == ""
        assert row["error_type"] == ""
        assert row["error_stack"] == ""
        assert row["duration_ms"] == 0
        assert row["tags"] == "{}"

    def test_event_with_span(self):
        from observability.schema import Event

        evt = Event(
            trace_id="t3",
            level="INFO",
            message="span",
            logger="trace",
            timestamp=3000.0,
            span_id="span-1",
            parent_span_id="span-0",
            event_type="span",
        )
        assert evt.span_id == "span-1"
        assert evt.parent_span_id == "span-0"

    def test_event_default_factory_tags(self):
        from observability.schema import Event

        evt1 = Event(trace_id="a", level="INFO", message="m", logger="l", timestamp=1.0)
        evt2 = Event(trace_id="b", level="INFO", message="m", logger="l", timestamp=2.0)
        assert evt1.tags == {}
        assert evt2.tags == {}
        evt2.tags["x"] = 1
        assert evt1.tags == {}
        assert evt2.tags == {"x": 1}


@pytest.mark.requirement("REQ-OBS-002")
class TestEventStore:
    def test_create_and_close(self):
        from observability.store import EventStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = EventStore(db_path)
            assert store._closed is False
            assert store._write_errors == 0
            store.close()
            assert store._closed is True
        finally:
            os.unlink(db_path)

    def test_write_after_close(self):
        from observability.schema import Event
        from observability.store import EventStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = EventStore(db_path)
            store.close()
            evt = Event(trace_id="t1", level="INFO", message="m", logger="l", timestamp=time.time())
            store.write(evt)
            assert store._write_errors == 1
        finally:
            os.unlink(db_path)

    def test_self_check_returns_metrics(self):
        from observability.store import EventStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = EventStore(db_path)
            check = store.self_check()
            assert "queue_size" in check
            assert "write_errors" in check
            assert "disk_errors" in check
            assert "disk_free_mb" in check
            assert "last_heartbeat" in check
            assert "db_path" in check
            assert check["write_errors"] == 0
            store.close()
        finally:
            os.unlink(db_path)

    @patch("observability.store.sqlite3.connect")
    def test_init_creates_schema(self, mock_connect):
        from observability.store import EventStore

        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        store = EventStore(":memory:")
        mock_conn.executescript.assert_called_once()
        store.close()

    def test_query_methods_with_real_db(self):
        from observability.schema import Event
        from observability.store import EventStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = EventStore(db_path)
            now = time.time()

            evt = Event(
                trace_id="q1",
                level="ERROR",
                message="query test error",
                logger="test",
                timestamp=now,
                error_type="RuntimeError",
            )
            store.write(evt)
            time.sleep(0.1)

            errors = store.recent_errors(seconds=60)
            assert len(errors) >= 1

            by_trace = store.by_trace("q1")
            assert len(by_trace) >= 1

            results = store.search("query test")
            assert len(results) >= 1

            stats = store.stats(seconds=60)
            assert "by_level" in stats
            assert stats["errors"] >= 1

            slow = store.slow_events(min_ms=0, seconds=60)
            assert len(slow) >= 1

            error_traces = store.error_trace_ids(seconds=60)
            assert len(error_traces) >= 1

            store.close()
        finally:
            os.unlink(db_path)

    def test_get_store_singleton(self):
        import observability.store as obs_store

        original = obs_store._store
        obs_store._store = None

        try:
            with patch.object(obs_store, "EventStore") as MockStore:
                mock_instance = MagicMock()
                MockStore.return_value = mock_instance

                s1 = obs_store.get_store()
                s2 = obs_store.get_store()
                assert s1 is s2
                MockStore.assert_called_once()
        finally:
            obs_store._store = original


class TestObservabilityHandler:
    def test_handler_emit(self):
        from observability.handler import ObservabilityHandler

        handler = ObservabilityHandler()

        mock_store = MagicMock()
        with patch("observability.handler.get_store", return_value=mock_store):
            with patch("observability.handler.current_trace_id", return_value="trace-h1"):
                record = logging.LogRecord(
                    name="test_logger",
                    level=logging.ERROR,
                    pathname=__file__,
                    lineno=42,
                    msg="handler test error",
                    args=(),
                    exc_info=None,
                )
                handler.emit(record)
                mock_store.write.assert_called_once()
                written_evt = mock_store.write.call_args[0][0]
                assert written_evt.trace_id == "trace-h1"
                assert written_evt.level == "ERROR"
                assert written_evt.logger == "test_logger"

    def test_handler_emit_with_exception(self):
        import sys

        from observability.handler import ObservabilityHandler

        handler = ObservabilityHandler()

        mock_store = MagicMock()
        with patch("observability.handler.get_store", return_value=mock_store):
            try:
                raise ValueError("test exception")
            except ValueError:
                exc_info = sys.exc_info()
                record = logging.LogRecord(
                    name="test",
                    level=logging.ERROR,
                    pathname=__file__,
                    lineno=42,
                    msg="error with exc",
                    args=(),
                    exc_info=exc_info,
                )
                handler.emit(record)
                written_evt = mock_store.write.call_args[0][0]
                assert written_evt.error_type == "ValueError"
                assert "test exception" in (written_evt.error_stack or "")

    def test_handler_silently_swallows_exceptions(self):
        from observability.handler import ObservabilityHandler

        handler = ObservabilityHandler()
        with patch("observability.handler.get_store", side_effect=RuntimeError("fail")):
            record = logging.LogRecord("t", logging.INFO, "f", 1, "msg", (), None)
            handler.emit(record)


class TestTrace:
    def test_current_trace_id_default(self):
        from observability.trace import current_trace_id
        assert current_trace_id() == ""

    def test_set_and_get_trace_id(self):
        from observability.trace import current_trace_id, set_trace_id
        set_trace_id("my-trace")
        assert current_trace_id() == "my-trace"

    def test_current_span_id_default(self):
        from observability.trace import current_span_id
        assert current_span_id() == ""

    @patch("observability.trace.get_store")
    def test_span_context_manager(self, mock_get_store):
        from observability.trace import set_trace_id, span

        set_trace_id("span-trace")
        mock_store = MagicMock()
        mock_get_store.return_value = mock_store

        with span("test-span", logger_name="test_logger", tags={"env": "test"}):
            pass

        mock_store.write.assert_called_once()
        written = mock_store.write.call_args[0][0]
        assert written.event_type == "span"
        assert written.message == "test-span"
        assert written.logger == "test_logger"
        assert written.tags == {"env": "test"}

    @patch("observability.trace.get_store")
    def test_span_records_error(self, mock_get_store):
        from observability.trace import set_trace_id, span

        set_trace_id("err-trace")
        mock_store = MagicMock()
        mock_get_store.return_value = mock_store

        with pytest.raises(ValueError, match="span error"):
            with span("failing-span"):
                raise ValueError("span error")

        written = mock_store.write.call_args[0][0]
        assert written.error_type == "ValueError"
        assert written.level == "ERROR"

    @patch("observability.trace.get_store")
    def test_span_auto_generates_trace_id(self, mock_get_store):
        from observability.trace import current_trace_id, set_trace_id, span

        # Clear the current trace_id so span must auto-generate one
        set_trace_id("")
        mock_store = MagicMock()
        mock_get_store.return_value = mock_store

        with span("auto-span"):
            pass

        written = mock_store.write.call_args[0][0]
        # trace_id should be auto-generated (not empty)
        assert written.trace_id != ""

    @patch("observability.trace.get_store")
    def test_span_nested(self, mock_get_store):
        from observability.trace import set_trace_id, span

        set_trace_id("nested-trace")
        mock_store = MagicMock()
        mock_get_store.return_value = mock_store

        with span("outer-span"):
            with span("inner-span"):
                pass

        # Two spans written (enter and exit of outer + enter and exit of inner = 2 calls)
        assert mock_store.write.call_count == 2
