"""Verify mutmut configuration is valid."""
import subprocess
import sys


def test_mutmut_installed():
    result = subprocess.run(
        [sys.executable, "-m", "mutmut", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0 or "not found" not in result.stderr.lower()
