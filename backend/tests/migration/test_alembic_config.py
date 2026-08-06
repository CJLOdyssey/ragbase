"""Verify Alembic migration configuration."""
from pathlib import Path


def test_alembic_ini_exists():
    assert Path("alembic.ini").exists(), "alembic.ini not found"


def test_alembic_env_exists():
    assert Path("backend/alembic/env.py").exists(), "backend/alembic/env.py not found"


def test_migrations_dir_exists():
    assert Path("backend/alembic/versions").is_dir(), "backend/alembic/versions/ not found"


def test_alembic_ini_has_sqlalchemy_url():
    content = Path("alembic.ini").read_text()
    assert "sqlalchemy.url" in content, "Missing sqlalchemy.url in alembic.ini"
