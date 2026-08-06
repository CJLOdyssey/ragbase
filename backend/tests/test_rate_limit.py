from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock()
    return redis


@pytest.fixture
def limiter():
    from core.infra.rate_limit import RateLimiter

    return RateLimiter(rate=5, window_seconds=10)


class TestRateLimiterIsAllowed:
    @pytest.mark.asyncio
    async def test_new_key_returns_true(self, limiter, mock_redis):
        mock_redis.incr.return_value = 1
        with patch("broker.get_redis", return_value=mock_redis):
            result = await limiter.is_allowed("test-key")
        assert result is True
        mock_redis.incr.assert_awaited_once()
        mock_redis.expire.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_within_limit_returns_true(self, limiter, mock_redis):
        mock_redis.incr.return_value = 3
        with patch("broker.get_redis", return_value=mock_redis):
            result = await limiter.is_allowed("test-key")
        assert result is True
        mock_redis.expire.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_exceeds_limit_returns_false(self, limiter, mock_redis):
        mock_redis.incr.return_value = 6
        with patch("broker.get_redis", return_value=mock_redis):
            result = await limiter.is_allowed("test-key")
        assert result is False
        mock_redis.expire.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_at_limit_returns_true(self, limiter, mock_redis):
        mock_redis.incr.return_value = 5
        with patch("broker.get_redis", return_value=mock_redis):
            result = await limiter.is_allowed("test-key")
        assert result is True

    @pytest.mark.asyncio
    async def test_rate_override_allows_more(self, limiter, mock_redis):
        mock_redis.incr.return_value = 8
        with patch("broker.get_redis", return_value=mock_redis):
            result = await limiter.is_allowed("test-key", rate_override=10)
        assert result is True

    @pytest.mark.asyncio
    async def test_rate_override_stricter_limit(self, limiter, mock_redis):
        mock_redis.incr.return_value = 3
        with patch("broker.get_redis", return_value=mock_redis):
            result = await limiter.is_allowed("test-key", rate_override=2)
        assert result is False

    @pytest.mark.asyncio
    async def test_different_keys_have_separate_limits(self, limiter, mock_redis):
        with patch("broker.get_redis", return_value=mock_redis):
            mock_redis.incr.return_value = 1
            result_a = await limiter.is_allowed("key-a")
            assert result_a is True

            mock_redis.incr.return_value = 1
            result_b = await limiter.is_allowed("key-b")
            assert result_b is True

    @pytest.mark.asyncio
    async def test_window_reset_allows_after_expiry(self, limiter, mock_redis):
        base_time = 1000000
        mock_redis.incr.return_value = 6
        with patch("broker.get_redis", return_value=mock_redis):
            with patch("core.infra.rate_limit.time") as mock_time:
                mock_time.time.return_value = base_time
                result = await limiter.is_allowed("test-key")
                assert result is False

        new_time = base_time + limiter.window + 1
        mock_redis.incr.return_value = 1
        with patch("broker.get_redis", return_value=mock_redis):
            with patch("core.infra.rate_limit.time") as mock_time:
                mock_time.time.return_value = new_time
                result = await limiter.is_allowed("test-key")
                assert result is True

    @pytest.mark.asyncio
    async def test_redis_exception_returns_true(self, limiter):
        broken_redis = AsyncMock()
        broken_redis.incr.side_effect = RuntimeError("redis down")
        with patch("broker.get_redis", return_value=broken_redis):
            result = await limiter.is_allowed("test-key")
        assert result is True

    @pytest.mark.asyncio
    async def test_default_rate_and_window(self):
        from core.infra.rate_limit import RateLimiter

        limiter = RateLimiter()
        assert limiter.rate == 60
        assert limiter.window == 60
