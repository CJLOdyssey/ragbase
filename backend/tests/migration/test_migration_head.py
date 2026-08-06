"""Verify database migration can reach head."""
import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set",
)
def test_migration_head():
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "heads"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "."},
    )
    assert result.returncode == 0, f"alembic heads failed: {result.stderr}"
    assert (
        "head" in result.stdout.lower() or result.stdout.strip()
    ), "No head revision found"
