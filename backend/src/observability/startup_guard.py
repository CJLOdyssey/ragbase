from typing import Any

"""Captures pre-startup crashes that the logging system can't reach.

Writes to a simple file, not the EventStore, because the EventStore
depends on the app being alive to initialize.
"""

import contextlib
import os
import tempfile
import time
from pathlib import Path

_MARKER_DIR = Path(tempfile.gettempdir()) / "agentstudio"
_MARKER_FILE = _MARKER_DIR / "startup.marker"
_CRASH_LOG = _MARKER_DIR / "startup_crash.log"


def mark_starting() -> None:
    """Write a marker before the app begins initializing."""
    _MARKER_DIR.mkdir(parents=True, exist_ok=True)
    _MARKER_FILE.write_text(f"starting pid={os.getpid()} at={time.time()}\n")
    _clean_crash_log()


def mark_started() -> None:
    """Update the marker once the app is fully initialized."""
    _MARKER_FILE.write_text(f"started pid={os.getpid()} at={time.time()}\n")


def mark_stopped() -> None:
    """Remove the startup marker file on shutdown."""
    with contextlib.suppress(Exception):
        _MARKER_FILE.unlink(missing_ok=True)


def record_crash(exc: BaseException) -> None:
    """Write a crash record that survives process death."""
    import traceback
    _MARKER_DIR.mkdir(parents=True, exist_ok=True)
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    _CRASH_LOG.write_text(
        f"crash at={time.time()} pid={os.getpid()}\n{tb}\n"
    )


def _clean_crash_log() -> None:
    with contextlib.suppress(Exception):
        _CRASH_LOG.unlink(missing_ok=True)


def health() -> dict[str, Any]:
    """Report startup status — callable even if the app never finished starting."""
    marker_ok = _MARKER_FILE.exists()
    crashed = _CRASH_LOG.exists()
    result: dict[str, Any] = {
        "marker_exists": marker_ok,
        "crashed": crashed,
    }
    if marker_ok:
        content = _MARKER_FILE.read_text().strip()
        parts = content.split()
        result["status"] = parts[0] if parts else "unknown"
        for part in parts[1:]:
            if "=" in part:
                k, v = part.split("=", 1)
                result[k] = v
    if crashed:
        result["crash_log"] = _CRASH_LOG.read_text()[:1000]
    return result
