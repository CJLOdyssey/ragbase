"""Tests for backend/orm/ — ORM table definitions."""
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

def test_tables_registered():
    from core.base import Base
    tables = {t.name for t in Base.metadata.sorted_tables}
    assert "sessions" in tables
    assert "agent_configs" not in tables
    assert "teams" not in tables
    assert "workflow_configs" not in tables
    assert "registered_tools" not in tables
    assert "mcp_servers" not in tables
    assert "registered_skills" not in tables
