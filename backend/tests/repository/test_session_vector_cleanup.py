"""Vector-chunk cleanup on session deletion (repository level, in-memory sqlite).

``vector_chunks`` is created via raw DDL in ``rag/rag_store.py`` (not ORM
metadata), so this suite creates a minimal table matching the DELETE-by-
session_id contract and drops it afterwards.
"""

import pytest
from core.infra.database import get_session_factory
from repository.session_repo import delete_vector_chunks_by_session
from sqlalchemy import text


@pytest.fixture(autouse=True)
async def _vector_chunks_table():
    """Create a minimal vector_chunks table (raw DDL like rag_store)."""
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(
            text(
                "CREATE TABLE IF NOT EXISTS vector_chunks ("
                "id TEXT PRIMARY KEY, session_id TEXT NOT NULL, text TEXT NOT NULL)"
            )
        )
        await session.commit()
    yield
    async with factory() as session:
        await session.execute(text("DROP TABLE IF EXISTS vector_chunks"))
        await session.commit()


async def _seed(session_id: str, count: int) -> None:
    factory = get_session_factory()
    async with factory() as session:
        for i in range(count):
            await session.execute(
                text(
                    "INSERT INTO vector_chunks (id, session_id, text) VALUES (:id, :sid, :t)"
                ),
                {"id": f"{session_id}-{i}", "sid": session_id, "t": "chunk"},
            )
        await session.commit()


class TestDeleteVectorChunksBySession:
    async def test_removes_only_matching_session_chunks(self):
        await _seed("s1", 2)
        await _seed("s2", 3)

        await delete_vector_chunks_by_session("s1")

        factory = get_session_factory()
        async with factory() as session:
            remaining = (
                await session.execute(text("SELECT session_id FROM vector_chunks"))
            ).scalars()
            assert list(remaining) == ["s2", "s2", "s2"]

    async def test_no_rows_is_noop(self):
        await delete_vector_chunks_by_session("missing")

        factory = get_session_factory()
        async with factory() as session:
            assert (
                await session.execute(text("SELECT count(*) FROM vector_chunks"))
            ).scalar() == 0
