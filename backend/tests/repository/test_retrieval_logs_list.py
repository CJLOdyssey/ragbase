"""Retrieval logs repository tests."""

import pytest

pytestmark = pytest.mark.unit

from core.infra.database import RetrievalLogDB, get_session_factory
from repository.retrieval_logs import (
    create_retrieval_log,
    list_retrieval_logs,
)


class TestCreateRetrievalLog:
    async def test_create_log(self):
        """Should create a retrieval log entry."""
        await create_retrieval_log(
            user_id="test_user",
            query="测试查询",
            latency_ms=100,
            hit_count=3,
            sources=[{"asset_id": "a1", "asset_name": "test.md", "similarity": 0.9}],
        )

        # Verify by querying the database
        factory = get_session_factory()
        async with factory() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(RetrievalLogDB).where(
                    RetrievalLogDB.user_id == "test_user",
                    RetrievalLogDB.query == "测试查询"
                )
            )
            log = result.scalar_one_or_none()

        assert log is not None
        assert log.user_id == "test_user"
        assert log.query == "测试查询"
        assert log.latency_ms == 100
        assert log.hit_count == 3

    async def test_create_log_with_session(self):
        """Should create log with session_id."""
        await create_retrieval_log(
            user_id="test_user",
            session_id="session_123",
            query="测试",
            latency_ms=50,
            hit_count=1,
        )

        # Verify by querying the database
        factory = get_session_factory()
        async with factory() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(RetrievalLogDB).where(
                    RetrievalLogDB.session_id == "session_123"
                )
            )
            log = result.scalar_one_or_none()

        assert log is not None
        assert log.session_id == "session_123"


class TestListRetrievalLogs:
    async def test_list_empty(self):
        """Should return empty list when no logs exist."""
        logs, total = await list_retrieval_logs(user_id="nonexistent_user")
        assert logs == []
        assert total == 0

    async def test_list_with_logs(self):
        """Should list logs for user."""
        # Create some logs
        await create_retrieval_log(
            user_id="test_user",
            query="查询1",
            latency_ms=100,
            hit_count=2,
        )
        await create_retrieval_log(
            user_id="test_user",
            query="查询2",
            latency_ms=200,
            hit_count=1,
        )

        logs, total = await list_retrieval_logs(user_id="test_user")
        assert total == 2
        assert len(logs) == 2
        assert all(log.user_id == "test_user" for log in logs)

    async def test_list_pagination(self):
        """Should support pagination."""
        # Create 5 logs
        for i in range(5):
            await create_retrieval_log(
                user_id="test_user",
                query=f"查询{i}",
                latency_ms=100 + i * 10,
                hit_count=i,
            )

        # Get page 1
        logs, total = await list_retrieval_logs(
            user_id="test_user",
            page=1,
            page_size=2,
        )
        assert total == 5
        assert len(logs) == 2

        # Get page 2
        logs, total = await list_retrieval_logs(
            user_id="test_user",
            page=2,
            page_size=2,
        )
        assert total == 5
        assert len(logs) == 2

    async def test_list_filter_empty_only(self):
        """Should filter logs with zero hits."""
        await create_retrieval_log(
            user_id="test_user",
            query="有结果",
            latency_ms=100,
            hit_count=2,
        )
        await create_retrieval_log(
            user_id="test_user",
            query="无结果",
            latency_ms=50,
            hit_count=0,
        )

        logs, total = await list_retrieval_logs(
            user_id="test_user",
            empty_only=True,
        )
        assert total == 1
        assert logs[0].hit_count == 0

    async def test_list_filter_min_hit_count(self):
        """Should filter logs by minimum hit count."""
        await create_retrieval_log(
            user_id="test_user",
            query="查询1",
            latency_ms=100,
            hit_count=1,
        )
        await create_retrieval_log(
            user_id="test_user",
            query="查询2",
            latency_ms=100,
            hit_count=3,
        )

        logs, total = await list_retrieval_logs(
            user_id="test_user",
            min_hit_count=2,
        )
        assert total == 1
        assert logs[0].hit_count == 3

    async def test_list_filter_max_latency(self):
        """Should filter logs by maximum latency."""
        await create_retrieval_log(
            user_id="test_user",
            query="快速查询",
            latency_ms=50,
            hit_count=1,
        )
        await create_retrieval_log(
            user_id="test_user",
            query="慢查询",
            latency_ms=500,
            hit_count=1,
        )

        logs, total = await list_retrieval_logs(
            user_id="test_user",
            max_latency_ms=100,
        )
        assert total == 1
        assert logs[0].latency_ms == 50
