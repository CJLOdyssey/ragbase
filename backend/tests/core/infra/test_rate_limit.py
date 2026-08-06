"""RateLimiter core tests: init, is_allowed, Redis failure mode."""

from unittest.mock import AsyncMock, patch

import pytest
from core.infra.rate_limit import DEFAULT_RATE, DEFAULT_WINDOW, RateLimiter


class TestInit:
    def test_defaults(self):
        r = RateLimiter()
        assert r.rate == DEFAULT_RATE
        assert r.window == DEFAULT_WINDOW

    def test_custom(self):
        r = RateLimiter(rate=30, window_seconds=120)
        assert r.rate == 30
        assert r.window == 120


class TestIsAllowed:
    @pytest.mark.asyncio
    async def test_first_request(self):
        mock = AsyncMock()
        mock.incr.return_value = 1
        with patch("broker.get_redis", return_value=mock):
            assert await RateLimiter(10).is_allowed("1.2.3.4") is True
            mock.incr.assert_called_once()

    @pytest.mark.asyncio
    async def test_within_limit(self):
        mock = AsyncMock()
        mock.incr.return_value = 5
        with patch("broker.get_redis", return_value=mock):
            assert await RateLimiter(10).is_allowed("1.2.3.4") is True

    @pytest.mark.asyncio
    async def test_exceeds_limit(self):
        mock = AsyncMock()
        mock.incr.return_value = 11
        with patch("broker.get_redis", return_value=mock):
            assert await RateLimiter(10).is_allowed("1.2.3.4") is False

    @pytest.mark.asyncio
    async def test_redis_failure_fails_open(self):
        with patch("broker.get_redis", side_effect=ConnectionError("down")):
            assert await RateLimiter(10).is_allowed("1.2.3.4") is True

    @pytest.mark.asyncio
    async def test_different_keys_independent(self):
        mock = AsyncMock()
        mock.incr.side_effect = [1, 1]
        with patch("broker.get_redis", return_value=mock):
            assert await RateLimiter(1).is_allowed("a") is True
            assert await RateLimiter(1).is_allowed("b") is True
