"""Tests for backend/app_lifespan.py — startup, Redis check, seed tools, shutdown."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAppLifespan:
    def test_mask_url_with_credentials(self):
        from core.app_lifespan import _mask_url
        result = _mask_url("postgresql://user:secret@localhost:5432/db")
        assert result == "postgresql:***@localhost:5432/db"

    def test_mask_url_without_credentials(self):
        from core.app_lifespan import _mask_url
        result = _mask_url("redis://localhost:6379/0")
        assert result == "redis://localhost:6379/0"

    def test_mask_url_empty(self):
        from core.app_lifespan import _mask_url
        assert _mask_url("") == ""

    def test_startup_report_includes_basic_info(self):
        from core.app_lifespan import _startup_report
        lines = _startup_report()
        assert len(lines) >= 3
        assert any("Application Starting" in line for line in lines)
        assert any("python=" in line for line in lines)
        assert any("Startup config complete" in line for line in lines)

    @pytest.mark.asyncio
    async def test_check_redis_success(self):
        from core.app_lifespan import _check_redis

        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True

        with patch("core.app_lifespan.get_redis", return_value=mock_redis):
            await _check_redis()
            mock_redis.ping.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_redis_connection_failure(self):
        from core.app_lifespan import _check_redis

        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = ConnectionError("Redis not available")

        with patch("core.app_lifespan.get_redis", return_value=mock_redis):
            await _check_redis()
            mock_redis.ping.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_redis_timeout(self):
        from core.app_lifespan import _check_redis

        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = TimeoutError("timeout")

        with patch("core.app_lifespan.get_redis", return_value=mock_redis):
            await _check_redis()
            mock_redis.ping.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_init_database_handles_exception(self):
        from core.app_lifespan import _init_database

        with patch("core.app_lifespan._do_init_db", side_effect=Exception("DB error")):
            await _init_database()

    @pytest.mark.asyncio
    async def test_shutdown_cancels_gc_task(self):
        import asyncio

        from core.app_lifespan import shutdown

        real_task = asyncio.create_task(asyncio.sleep(9999))
        mock_app = MagicMock()
        mock_app.state.gc_task = real_task
        mock_app.state.retention_task = None
        mock_app.title = "test"

        await shutdown(mock_app)
        assert real_task.cancelled()

    @pytest.mark.asyncio
    async def test_startup_calls_config_and_init(self):
        from core.app_lifespan import startup

        mock_app = MagicMock()
        mock_app.state = MagicMock()

        with patch("core.app_lifespan.load_config"):
            with patch("core.app_lifespan._init_database", new_callable=AsyncMock):
                with patch("core.app_lifespan._check_redis", new_callable=AsyncMock):
                    with patch("core.app_lifespan.mark_started"):
                        await startup(mock_app)
                        assert hasattr(mock_app.state, "gc_task")

    @pytest.mark.asyncio
    async def test_startup_handles_exception(self):
        from core.app_lifespan import startup

        mock_app = MagicMock()
        mock_app.state = MagicMock()

        with patch("core.app_lifespan.load_config"):
            with patch("core.app_lifespan._init_database", side_effect=RuntimeError("Fatal")):
                with patch("core.app_lifespan.record_crash") as mock_record:
                    with pytest.raises(RuntimeError, match="Fatal"):
                        await startup(mock_app)
                    mock_record.assert_called_once()

    def test_env_helper(self):
        from core.app_lifespan import _env

        with patch("core.app_lifespan.os.environ", {"MY_KEY": "my_value"}):
            assert _env("MY_KEY") == "my_value"
            assert _env("NONEXISTENT", "default") == "default"
            assert _env("NONEXISTENT2") == ""
