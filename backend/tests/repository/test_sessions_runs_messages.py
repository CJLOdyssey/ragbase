import pytest
pytestmark = pytest.mark.integration
"""Repository tests for session, run, and message CRUD operations.

Uses conftest fixtures (db_engine, async_session) against in-memory SQLite.
"""

import uuid

from repository.message_repo import (
    get_messages,
    get_run_messages,
    get_session_messages,
    save_message,
)
from repository.run_repo import (
    create_run,
    get_run,
    get_runs,
    get_runs_by_session_ids,
    get_session_runs,
    update_run_result,
    update_run_status,
)
from repository.session_repo import (
    create_session,
    delete_session,
    get_session,
    get_sessions,
    update_session_title,
)

# ── Session Tests ──────────────────────────────────────────────────────


@pytest.mark.requirement("REQ-SES-001")
@pytest.mark.requirement("REQ-SES-003")
class TestSessionRepo:
    async def test_create_and_get_session(self, db_engine):
        title = "Test Session"
        created = await create_session(title=title, user_id="test_user")
        assert created.id is not None
        assert created.title == title
        assert created.user_id == "test_user"

        fetched = await get_session(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.title == title

    async def test_get_session_not_found(self, db_engine):
        result = await get_session("nonexistent-id")
        assert result is None

    @pytest.mark.requirement("REQ-SES-002")
    async def test_get_sessions_default(self, db_engine):
        await create_session(title="Session A", user_id="u1")
        await create_session(title="Session B", user_id="u2")
        sessions = await get_sessions(limit=10)
        assert len(sessions) >= 2

    async def test_get_sessions_filtered_by_user(self, db_engine):
        await create_session(title="U1 Session", user_id="u_filter")
        await create_session(title="Other", user_id="other")
        filtered = await get_sessions(user_id="u_filter")
        assert all(s.user_id == "u_filter" for s in filtered)

    async def test_get_sessions_empty(self, db_engine):
        # Use a known-nonexistent user filter
        sessions = await get_sessions(user_id="no_such_user_xyz")
        assert sessions == []

    async def test_update_session_title(self, db_engine):
        sess = await create_session(title="Original")
        updated = await update_session_title(sess.id, "Updated Title")
        assert updated is not None
        assert updated.title == "Updated Title"

        fetched = await get_session(sess.id)
        assert fetched is not None
        assert fetched.title == "Updated Title"

    async def test_update_session_title_not_found(self, db_engine):
        result = await update_session_title("nonexistent", "Nope")
        assert result is None

    @pytest.mark.requirement("REQ-SES-004")
    async def test_delete_session(self, db_engine):
        sess = await create_session(title="To Delete")
        await delete_session(sess.id)
        fetched = await get_session(sess.id)
        assert fetched is None

    async def test_delete_session_not_found(self, db_engine):
        # Should not raise
        await delete_session("nonexistent")


# ── Run Tests ──────────────────────────────────────────────────────────


class TestRunRepo:
    async def test_create_and_get_run(self, db_engine):
        run_id = await create_run(requirement="Build a feature")
        assert run_id is not None

        fetched = await get_run(run_id)
        assert fetched is not None
        assert fetched.id == run_id
        assert fetched.requirement == "Build a feature"
        assert fetched.status == "pending"

    async def test_get_run_not_found(self, db_engine):
        result = await get_run("nonexistent-run-id")
        assert result is None

    async def test_create_run_with_session(self, db_engine):
        sess = await create_session(title="Parent Session")
        run_id = await create_run(requirement="With session", session_id=sess.id)
        assert run_id is not None

        runs = await get_session_runs(sess.id)
        assert len(runs) == 1
        assert runs[0].id == run_id

    async def test_get_session_runs_empty(self, db_engine):
        runs = await get_session_runs("no-such-session")
        assert runs == []

    async def test_get_runs(self, db_engine):
        sess = await create_session(title="Runs Test")
        r1 = await create_run(requirement="Run 1", session_id=sess.id)
        r2 = await create_run(requirement="Run 2", session_id=sess.id)
        all_runs = await get_runs()
        ids = [r.id for r in all_runs]
        assert r1 in ids
        assert r2 in ids

    async def test_get_runs_by_session_ids(self, db_engine):
        sess1 = await create_session(title="S1")
        sess2 = await create_session(title="S2")
        r1 = await create_run(requirement="R1", session_id=sess1.id)
        r2 = await create_run(requirement="R2", session_id=sess2.id)

        grouped = await get_runs_by_session_ids([sess1.id, sess2.id])
        assert sess1.id in grouped
        assert sess2.id in grouped
        assert any(r.id == r1 for r in grouped[sess1.id])
        assert any(r.id == r2 for r in grouped[sess2.id])

    async def test_get_runs_by_session_ids_empty_input(self, db_engine):
        result = await get_runs_by_session_ids([])
        assert result == {}

    async def test_update_run_status(self, db_engine):
        run_id = await create_run(requirement="Status Test")
        await update_run_status(run_id, "running")
        fetched = await get_run(run_id)
        assert fetched is not None
        assert fetched.status == "running"

    async def test_update_run_status_not_found(self, db_engine):
        # Should not raise
        await update_run_status("nonexistent", "running")

    async def test_update_run_result(self, db_engine):
        run_id = await create_run(requirement="Result Test")
        await update_run_result(
            run_id,
            pm_document="Doc",
            code="print('hello')",
            review="LGTM",
            approved=True,
            status="converged",
        )
        fetched = await get_run(run_id)
        assert fetched is not None
        assert fetched.status == "converged"
        assert fetched.code == "print('hello')"

    async def test_update_run_result_not_found(self, db_engine):
        await update_run_result(
            "nonexistent",
            pm_document="",
            code="",
            review="",
            approved=False,
            status="error",
        )


# ── Message Tests ──────────────────────────────────────────────────────


class TestMessageRepo:
    async def _create_run_with_message(self, db_engine, content="Hello", thinking=None):
        """Helper: creates a session + run + message, returns ids."""
        sess = await create_session(title="Msg Session")
        run_id = await create_run(requirement="Msg Run", session_id=sess.id)
        await save_message(
            run_id=run_id,
            role="user",
            agent_name="User",
            content=content,
            round_number=1,
            thinking=thinking,
        )
        return sess.id, run_id

    async def test_save_and_get_messages(self, db_engine):
        _, run_id = await self._create_run_with_message(db_engine, "Hello World")
        messages = await get_messages(run_id)
        assert len(messages) == 1
        assert messages[0].content == "Hello World"
        assert messages[0].role == "user"

    async def test_save_message_with_thinking(self, db_engine):
        _, run_id = await self._create_run_with_message(
            db_engine, "Thoughtful", thinking="deep thoughts"
        )
        msgs = await get_messages(run_id)
        assert msgs[0].thinking == "deep thoughts"

    async def test_get_messages_empty(self, db_engine):
        msgs = await get_messages("no-such-run")
        assert msgs == []

    async def test_get_run_messages(self, db_engine):
        _, run_id = await self._create_run_with_message(db_engine, "Run Msg")
        msgs = await get_run_messages(run_id)
        assert len(msgs) == 1

    async def test_get_session_messages(self, db_engine):
        sess_id, run_id = await self._create_run_with_message(db_engine, "Session Msg")
        msgs = await get_session_messages(sess_id)
        assert len(msgs) == 1
        assert msgs[0].content == "Session Msg"

    async def test_get_session_messages_empty(self, db_engine):
        msgs = await get_session_messages("no-such-session")
        assert msgs == []

    async def test_get_session_messages_exclude_run(self, db_engine):
        sess_id, run_id = await self._create_run_with_message(db_engine, "Keep")
        # Create another run in same session
        run2 = await create_run(requirement="Excluded Run", session_id=sess_id)
        await save_message(
            run_id=run2, role="user", agent_name="User", content="Exclude Me", round_number=1
        )
        msgs = await get_session_messages(sess_id, exclude_run_id=run2)
        assert len(msgs) == 1
        assert msgs[0].content == "Keep"

    async def test_multiple_messages_ordered(self, db_engine):
        sess = await create_session(title="Order Test")
        run_id = await create_run(requirement="Order", session_id=sess.id)
        await save_message(run_id=run_id, role="user", agent_name="User", content="First", round_number=1)
        await save_message(
            run_id=run_id, role="assistant", agent_name="Agent", content="Second", round_number=2
        )
        msgs = await get_messages(run_id)
        assert len(msgs) == 2
        assert msgs[0].content == "First"
        assert msgs[1].content == "Second"
