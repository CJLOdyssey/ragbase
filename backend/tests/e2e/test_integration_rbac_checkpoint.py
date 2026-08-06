"""Integration tests: RBAC ownership + persistent checkpoint interaction."""

import os

import pytest
from checkpoint import create_checkpointer


class TestOwnedAgentRuns:
    """Verify that checkpoint + RBAC ownership interoperate correctly."""

    def test_sqlite_checkpointer_create(self):
        os.environ["CHECKPOINTER_BACKEND"] = "sqlite"
        os.environ["CHECKPOINTER_DSN"] = "./.test_checkpoints_integration.db"
        try:
            cp = create_checkpointer()
            assert cp is not None
            assert hasattr(cp, "put")
            assert hasattr(cp, "get")
            assert hasattr(cp, "list")
        finally:
            # clean up
            if os.path.exists("./.test_checkpoints_integration.db"):
                os.remove("./.test_checkpoints_integration.db")

    def test_apply_owner_filter_exists(self):
        from core.infra.database import SessionDB
        from repository.core import apply_owner_filter
        from sqlalchemy import select

        stmt = select(SessionDB)
        result = apply_owner_filter(stmt, SessionDB, owner_id=None)
        assert result is stmt

    @pytest.mark.skipif(
        os.environ.get("AUTH_MODE") != "rbac",
        reason="RBAC integration test requires AUTH_MODE=rbac",
    )
    def test_get_current_user_dependency_importable(self):
        from auth import CurrentUser, get_current_user

        assert callable(get_current_user)
        assert CurrentUser(id="test", username="test", roles=["admin"])
