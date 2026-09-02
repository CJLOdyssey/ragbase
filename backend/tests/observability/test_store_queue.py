"""Tests for backend/observability/store.py uncovered edge cases: queue.Full and writer_loop."""

import contextlib
import os
import queue
import sqlite3
import tempfile
import threading
import time
from unittest.mock import MagicMock, patch

import pytest
from observability.schema import SCHEMA_SQL, Event


class TestStoreQueueFull:
    """Cover store.py lines 66-67: queue.Full exception in write()."""

    def test_write_increments_errors_on_queue_full(self):
        from observability.store import EventStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = EventStore(db_path)
            store._queue = MagicMock(spec=queue.SimpleQueue)
            store._queue.put.side_effect = queue.Full

            evt = Event(trace_id="t", level="INFO", message="m", logger="l", timestamp=time.time())
            store.write(evt)
            assert store._write_errors == 1
            store.close()
        finally:
            os.unlink(db_path)

    def test_write_after_close_then_queue_full(self):
        from observability.store import EventStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = EventStore(db_path)
            store.close()
            evt = Event(trace_id="t", level="INFO", message="m", logger="l", timestamp=time.time())
            # Close takes priority over queue.Full
            store.write(evt)
            assert store._write_errors == 1
        finally:
            os.unlink(db_path)


class TestWriterLoopException:
    """Writer-loop resilience: a failed batch must not kill the writer thread.

    Contract (post QA A9): per-batch errors are caught, counted in
    ``write_errors`` and the loop continues — only BaseException (e.g.
    SystemExit) escapes through ``finally: conn.close()``.
    """

    def _bare_store(self, db_path):
        """EventStore instance without __init__ (no real writer thread)."""
        import observability.store as store_mod

        s = store_mod.EventStore.__new__(store_mod.EventStore)
        s._db_path = db_path
        s._queue = queue.SimpleQueue()
        s._closed = False
        s._write_errors = 0
        return s

    def test_writer_loop_survives_bad_path(self):
        """sqlite3.connect failure at startup propagates (constructor already
        guarantees the schema exists, so this only fires on broken paths)."""
        from observability.store import EventStore

        with pytest.raises(sqlite3.OperationalError):
            EventStore(db_path="/nonexistent_dir/events.db")

    def test_writer_loop_commits_batch(self):
        """Verify the writer loop batch-inserts multiple items into SQLite."""

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            # Create schema
            conn = sqlite3.connect(db_path)
            conn.executescript(SCHEMA_SQL)
            conn.close()

            s = self._bare_store(db_path)
            for i in range(5):
                s._queue.put({"timestamp": time.time() + i, "trace_id": f"t{i}", "span_id": "",
                              "parent_span_id": "", "level": "INFO", "logger": "l",
                              "message": f"msg{i}", "error_type": "", "error_stack": "",
                              "duration_ms": 0, "tags": "{}", "event_type": "log"})

            t = threading.Thread(target=s._writer_loop, daemon=True)
            t.start()
            time.sleep(0.5)

            conn = sqlite3.connect(db_path)
            count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            conn.close()
            assert count >= 5
        finally:
            os.unlink(db_path)

    def test_writer_loop_except_and_finally(self):
        """批次1 写失败 → 行丢弃 + write_errors++，线程必须存活继续消费；
        批次2 正常提交；BaseException（SystemExit）经 finally 关闭连接退出。

        注意 writer 会把队列中现有行合并为一个批次（≤100），因此三个阶段
        通过「主线程逐批投递 + 轮询等待」驱动，而非一次性塞入多行。
        """
        import observability.store as store_mod

        s = self._bare_store(":memory:")
        mock_conn = MagicMock()
        calls = {"n": 0}

        def executemany_side_effect(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("simulated executemany error")
            if calls["n"] == 3:
                raise SystemExit("test loop exit")
            return None

        mock_conn.executemany.side_effect = executemany_side_effect

        mock_sqlite3 = MagicMock()
        mock_sqlite3.connect.return_value = mock_conn

        row = {"timestamp": 1, "trace_id": "t", "span_id": "", "parent_span_id": "",
               "level": "INFO", "logger": "l", "message": "m", "error_type": "",
               "error_stack": "", "duration_ms": 0, "tags": "{}", "event_type": "log"}

        def _put_and_wait_for(pred, desc):
            s._queue.put(dict(row))
            deadline = time.time() + 5
            while not pred():
                if time.time() > deadline:
                    raise AssertionError(f"timeout waiting for {desc}")
                time.sleep(0.01)

        original_sqlite = store_mod.sqlite3
        original_sleep = store_mod.time.sleep
        store_mod.sqlite3 = mock_sqlite3
        store_mod.time.sleep = lambda *_: None  # 失败退避不拖慢测试

        def _writer_runner() -> None:
            # SystemExit 是 BaseException 子类，直接在线程里逃逸会被 pytest
            # 记为 PytestUnhandledThreadExceptionWarning；此处仅验证
            # "连接经 finally 关闭" 的可观测结果（mock_conn.close 调用计数）。
            with contextlib.suppress(BaseException):
                s._writer_loop()

        try:
            t = threading.Thread(target=_writer_runner, daemon=True)
            t.start()

            # 批次1：写失败被吞掉并计数，线程存活
            _put_and_wait_for(lambda: s._write_errors == 1, "batch-1 drop")
            # 批次2：正常提交
            _put_and_wait_for(lambda: mock_conn.commit.call_count == 1, "batch-2 commit")
            # 批次3：BaseException 逃逸 → finally 关闭连接、线程结束
            _put_and_wait_for(lambda: mock_conn.close.call_count == 1, "batch-3 exit")
            t.join(timeout=5)
            assert s._write_errors == 1
            assert mock_conn.commit.call_count == 1
        finally:
            store_mod.sqlite3 = original_sqlite
            store_mod.time.sleep = original_sleep


class TestStoreWriteDiscardZeroDisk:
    """Cover store.py line 60: free == 0 should not be treated as disk-full."""

    def test_write_allows_when_disk_free_is_zero(self):
        """When _disk_free returns 0, the check 0 < 0 < MIN is false, so write proceeds."""
        from observability.store import EventStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = EventStore(db_path)
            with patch.object(store, "_disk_free", return_value=0):
                store._disk_errors = 0
                evt = Event(trace_id="t", level="INFO", message="m", logger="l", timestamp=time.time())
                store.write(evt)
                assert store._disk_errors == 0
            store.close()
        finally:
            os.unlink(db_path)

    def test_write_allows_when_disk_free_is_negative(self):
        """When _disk_free returns -1 (error), write proceeds."""
        from observability.store import EventStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = EventStore(db_path)
            with patch.object(store, "_disk_free", return_value=-1.0):
                store._disk_errors = 0
                evt = Event(trace_id="t", level="INFO", message="m", logger="l", timestamp=time.time())
                store.write(evt)
                assert store._disk_errors == 0
            store.close()
        finally:
            os.unlink(db_path)


class TestStoreSelfCheckDiskFreeNegative:
    """Cover store.py line 76: disk_free_mb when free <= 0."""

    def test_self_check_disk_free_negative(self):
        from observability.store import EventStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = EventStore(db_path)
            with patch.object(store, "_disk_free", return_value=-1.0):
                check = store.self_check()
                assert check["disk_free_mb"] == -1.0
            store.close()
        finally:
            os.unlink(db_path)


class TestStoreWriterSize:
    """Cover store.py _writer_size helper."""

    def test_writer_size_returns_qsize(self):
        from observability.store import _writer_size
        q = queue.SimpleQueue()
        assert _writer_size(q) == 0
        q.put("item")
        assert _writer_size(q) == 1
