"""Verify migration files are properly formatted."""

from pathlib import Path

import pytest

# Repo root regardless of pytest's working directory.
REPO_ROOT = Path(__file__).resolve().parents[3]
VERSIONS_DIR = REPO_ROOT / "backend/alembic/versions"


def test_migration_files_have_revision():
    if not VERSIONS_DIR.exists():
        pytest.skip("alembic/versions/ not present")

    files = sorted(VERSIONS_DIR.glob("*.py"))
    assert files, "no migration files found under alembic/versions/"

    for f in files:
        content = f.read_text(encoding="utf-8")
        assert "revision" in content, f"{f.name} missing revision"
        assert "down_revision" in content, f"{f.name} missing down_revision"
