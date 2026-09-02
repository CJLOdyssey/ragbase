"""Verify database migration chain reaches exactly one head."""

import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set",
)
def test_migration_single_head():
    """``alembic heads`` 必须成功且恰好输出一个 (head) 修订 —— 多 head 即分叉。"""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "heads"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "."},
    )
    assert result.returncode == 0, f"alembic heads failed: {result.stderr}"

    heads = [line for line in result.stdout.splitlines() if "(head)" in line]
    assert len(heads) == 1, f"expected exactly one head, got {len(heads)}: {result.stdout}"
