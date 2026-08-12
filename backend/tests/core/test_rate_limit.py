"""Tests for the per-user sliding-window rate limiter (OWASP LLM10)."""

from core.rate_limit import SlidingWindowLimiter


class TestSlidingWindowLimiter:
    def test_allows_up_to_max(self):
        limiter = SlidingWindowLimiter(max_calls=3, window_seconds=60)
        assert limiter.allow("u1", now=100.0)
        assert limiter.allow("u1", now=101.0)
        assert limiter.allow("u1", now=102.0)
        assert not limiter.allow("u1", now=103.0)

    def test_window_rollover_frees_slots(self):
        limiter = SlidingWindowLimiter(max_calls=2, window_seconds=60)
        assert limiter.allow("u1", now=100.0)
        assert limiter.allow("u1", now=110.0)
        assert not limiter.allow("u1", now=120.0)
        assert not limiter.allow("u1", now=159.0)  # 100 still inside window
        assert limiter.allow("u1", now=160.0)  # 100 expired at cutoff
        assert not limiter.allow("u1", now=160.0)  # [110, 160] full again

    def test_users_are_isolated(self):
        limiter = SlidingWindowLimiter(max_calls=1, window_seconds=60)
        assert limiter.allow("u1", now=100.0)
        assert not limiter.allow("u1", now=101.0)
        assert limiter.allow("u2", now=101.0)

    def test_empty_key_space_does_not_leak(self):
        limiter = SlidingWindowLimiter(max_calls=1, window_seconds=60)
        limiter.allow("u1", now=100.0)
        # allow() on a different key must not affect u1's window
        assert limiter.allow("u2", now=150.0)
