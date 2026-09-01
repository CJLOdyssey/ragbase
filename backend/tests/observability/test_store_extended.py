"""Additional tests for backend/observability/store.py — cleanup, edge cases, error paths."""

import os
import tempfile
import time
from unittest.mock import patch

from observability.schema import Event


class TestEventStoreCleanup:
    def test_cleanup_deletes_old_events(self):
        from observability.store import EventStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = EventStore(db_path)
            # Write an event with old timestamp
            old_ts = time.time() - 40 * 86400  # 40 days ago
            evt = Event(
                trace_id="old",
                level="INFO",
                message="old event",
                logger="test",
                timestamp=old_ts,
            )
            store.write(evt)
            time.sleep(0.2)

            # Write a recent event
            recent_ts = time.time()
            evt2 = Event(
                trace_id="recent",
                level="INFO",
                message="recent event",
                logger="test",
                timestamp=recent_ts,
            )
            store.write(evt2)
            time.sleep(0.2)

            deleted = store.cleanup(retention_days=30)
            assert deleted >= 1

            # Recent event should still be there
            recent = store.search("recent")
            assert len(recent) >= 1

            store.close()
        finally:
            os.unlink(db_path)

    def test_cleanup_with_zero_days_returns_zero(self):
        from observability.store import EventStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = EventStore(db_path)
            assert store.cleanup(retention_days=0) == 0
            assert store.cleanup(retention_days=-1) == 0
            store.close()
        finally:
            os.unlink(db_path)

    def test_cleanup_exception_returns_negative_one(self):
        from observability.store import EventStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = EventStore(db_path)
            store.close()
            # connect with a bad path to trigger cleanup error
            store._db_path = "/nonexistent/path/events.db"
            result = store.cleanup(retention_days=30)
            assert result == -1
        finally:
            os.unlink(db_path)

    def test_cleanup_connects_inline(self):
        from observability.store import EventStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = EventStore(db_path)
            deleted = store.cleanup(retention_days=365)
            assert deleted >= 0
            store.close()
        finally:
            os.unlink(db_path)


class TestEventStoreDiskFree:
    def test_disk_free_returns_free_bytes(self):
        from observability.store import EventStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = EventStore(db_path)
            free = store._disk_free()
            assert free > 0 or free == -1.0
            store.close()
        finally:
            os.unlink(db_path)

    def test_disk_free_negative_on_oserror(self):
        from observability.store import EventStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            with patch("shutil.disk_usage", side_effect=OSError("disk error")):
                store = EventStore(db_path)
                assert store._disk_free() == -1.0
                store.close()
        finally:
            os.unlink(db_path)


class TestEventStoreWriteErrors:
    def test_write_increments_write_errors_after_close(self):
        from observability.store import EventStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = EventStore(db_path)
            store.close()
            assert store._write_errors == 0
            evt = Event(trace_id="t", level="INFO", message="m", logger="l", timestamp=time.time())
            store.write(evt)
            assert store._write_errors == 1
        finally:
            os.unlink(db_path)

    def test_write_rejects_when_disk_full(self):
        from observability.store import EventStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = EventStore(db_path)
            with patch.object(store, "_disk_free", return_value=1):  # very low free space
                store._disk_errors = 0
                evt = Event(trace_id="t", level="INFO", message="m", logger="l", timestamp=time.time())
                store.write(evt)
                assert store._disk_errors == 1
            store.close()
        finally:
            os.unlink(db_path)


class TestEventStoreSelfCheck:
    def test_self_check_includes_all_keys(self):
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
            assert "disk_min_free_mb" in check
            assert "writer_alive" in check
            assert "closed" in check
            assert "last_heartbeat" in check
            assert "db_path" in check
            store.close()
        finally:
            os.unlink(db_path)

    def test_self_check_reflects_write_errors(self):
        from observability.store import EventStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = EventStore(db_path)
            store.close()
            evt = Event(trace_id="t", level="INFO", message="m", logger="l", timestamp=time.time())
            store.write(evt)
            check = store.self_check()
            assert check["write_errors"] == 1
        finally:
            os.unlink(db_path)


class TestEventStoreDbReconnect:
    def test_query_opts_readonly_mode(self):
        from observability.store import EventStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = EventStore(db_path)
            result = store._query("SELECT 1")
            assert len(result) >= 1
            store.close()
        finally:
            os.unlink(db_path)
