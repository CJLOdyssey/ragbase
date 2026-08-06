"""Tests for backend/observability/startup_guard.py — startup markers and crash logs."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from observability.startup_guard import (
    health,
    mark_started,
    mark_starting,
    mark_stopped,
    record_crash,
)


@pytest.fixture
def temp_marker_dir():
    """Redirect marker dir to a temp location."""
    with tempfile.TemporaryDirectory() as td:
        marker_dir = Path(td) / "agentstudio"
        marker_file = marker_dir / "startup.marker"
        crash_log = marker_dir / "startup_crash.log"
        with patch("observability.startup_guard._MARKER_DIR", marker_dir), \
             patch("observability.startup_guard._MARKER_FILE", marker_file), \
             patch("observability.startup_guard._CRASH_LOG", crash_log):
            yield marker_dir, marker_file, crash_log


class TestMarkStarting:
    def test_creates_marker_dir_and_file(self, temp_marker_dir):
        marker_dir, marker_file, _ = temp_marker_dir
        mark_starting()
        assert marker_dir.exists()
        assert marker_file.exists()
        content = marker_file.read_text()
        assert "starting" in content
        assert "pid=" in content

    def test_cleans_old_crash_log(self, temp_marker_dir):
        marker_dir, marker_file, crash_log = temp_marker_dir
        marker_dir.mkdir(parents=True, exist_ok=True)
        crash_log.write_text("old crash")
        mark_starting()
        assert not crash_log.exists()
        assert marker_file.exists()


class TestMarkStarted:
    def test_updates_marker(self, temp_marker_dir):
        _, marker_file, _ = temp_marker_dir
        mark_starting()
        mark_started()
        content = marker_file.read_text()
        assert "started" in content


class TestMarkStopped:
    def test_removes_marker(self, temp_marker_dir):
        _, marker_file, _ = temp_marker_dir
        mark_starting()
        assert marker_file.exists()
        mark_stopped()
        assert not marker_file.exists()

    def test_ignores_missing_file(self, temp_marker_dir):
        mark_stopped()


class TestRecordCrash:
    def test_writes_crash_log(self, temp_marker_dir):
        marker_dir, _, crash_log = temp_marker_dir
        try:
            raise ValueError("test crash message")
        except ValueError as exc:
            record_crash(exc)

        assert crash_log.exists()
        content = crash_log.read_text()
        assert "crash at=" in content
        assert "ValueError" in content
        assert "test crash message" in content

    def test_creates_marker_dir_if_missing(self, temp_marker_dir):
        # Remove the dir tree so record_crash must re-create it
        import shutil
        shutil.rmtree(str(temp_marker_dir[0]), ignore_errors=True)
        try:
            raise RuntimeError("boom")
        except RuntimeError as exc:
            record_crash(exc)

        # Check the fixture-provided crash_log path (patched into module)
        assert temp_marker_dir[2].exists()
        assert "RuntimeError" in temp_marker_dir[2].read_text()


class TestHealth:
    def test_no_marker_no_crash(self, temp_marker_dir):
        result = health()
        assert result["marker_exists"] is False
        assert result["crashed"] is False

    def test_marker_exists(self, temp_marker_dir):
        mark_starting()
        result = health()
        assert result["marker_exists"] is True
        assert result["status"] == "starting"
        assert "pid" in result

    def test_started_status(self, temp_marker_dir):
        mark_starting()
        mark_started()
        result = health()
        assert result["marker_exists"] is True
        assert result["status"] == "started"

    def test_crash_detected(self, temp_marker_dir):
        try:
            raise SystemError("fatal")
        except SystemError as exc:
            record_crash(exc)

        result = health()
        assert result["crashed"] is True
        assert result["crash_log"] is not None
        assert "SystemError" in result["crash_log"]

    def test_crash_log_truncated(self, temp_marker_dir):
        # Write a short marker so marker_exists is True, plus a long crash log
        mark_starting()
        crash_log = temp_marker_dir[2]
        long_content = "x" * 2000
        crash_log.write_text(long_content)
        result = health()
        assert result["crashed"] is True
        assert result["crash_log"] is not None
        assert len(result["crash_log"]) <= 1000

    def test_handler_path(self, temp_marker_dir):
        mark_starting()
        result = health()
        assert result["marker_exists"] is True
        assert result["status"] == "starting"
