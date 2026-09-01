"""Tests for health.py repository — database and Redis health checks."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from repository.health import check_database, check_redis


class TestCheckDatabase:
    async def test_returns_ok_on_success(self, db_engine):
        result = await check_database()
        assert result == "ok"

    async def test_returns_error_message_on_failure(self):
        with patch("repository.health.get_session_factory", side_effect=RuntimeError("DB down")):
            result = await check_database()
            assert "DB down" in result


class TestCheckRedis:
    async def test_returns_ok_on_success(self):
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        with patch("repository.health.get_redis", return_value=mock_redis):
            result = await check_redis()
            assert result == "ok"

    async def test_returns_error_message_on_failure(self):
        with patch("repository.health.get_redis", side_effect=ConnectionError("Redis unreachable")):
            result = await check_redis()
            assert "Redis unreachable" in result
