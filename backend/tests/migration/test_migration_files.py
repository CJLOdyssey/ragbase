"""Verify migration files are properly formatted."""
from pathlib import Path


def test_migration_files_have_revision():
    versions_dir = Path("backend/alembic/versions")
    if not versions_dir.exists():
        return  # Skip if no migrations yet

    for f in versions_dir.glob("*.py"):
        content = f.read_text()
        assert "revision" in content, f"{f.name} missing revision"
        assert "down_revision" in content, f"{f.name} missing down_revision"
