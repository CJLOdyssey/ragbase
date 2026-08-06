"""Circuit breaker core lifecycle tests: init, state transitions, timeout."""

import asyncio

import pytest
from core.infra.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, State


class TestInit:
    def test_defaults(self):
        cb = CircuitBreaker(name="test")
        assert cb.name == "test"
        assert cb.maxfail == 5
        assert cb.reset_timeout == 60.0
        assert cb.half_open_max_calls == 1
        assert cb.state == State.CLOSED
        assert cb.failures == 0

    def test_custom_thresholds(self):
        cb = CircuitBreaker(name="custom", maxfail=3, reset_timeout=10.0, half_open_max_calls=2)
        assert cb.maxfail == 3
        assert cb.reset_timeout == 10.0

    def test_status_method(self):
        cb = CircuitBreaker(name="monitor")
        st = cb.status()
        assert st["state"] == "closed"
        assert st["failures"] == 0


class TestClosedToOpen:
    @pytest.mark.asyncio
    async def test_accumulate_below_threshold(self):
        cb = CircuitBreaker(name="t", maxfail=5)
        for _ in range(4):
            await cb._acquire()
            await cb._on_failure()
        assert cb.state == State.CLOSED

    @pytest.mark.asyncio
    async def test_maxfail_opens(self):
        cb = CircuitBreaker(name="t", maxfail=3)
        for _ in range(3):
            await cb._acquire()
            await cb._on_failure()
        assert cb.state == State.OPEN

    @pytest.mark.asyncio
    async def test_acquire_raises_when_open(self):
        cb = CircuitBreaker(name="t", maxfail=1)
        await cb._acquire()
        await cb._on_failure()
        with pytest.raises(CircuitBreakerOpenError):
            await cb._acquire()


class TestClosedSuccess:
    @pytest.mark.asyncio
    async def test_success_resets_counter(self):
        cb = CircuitBreaker(name="t", maxfail=3)
        for _ in range(2):
            await cb._acquire()
            await cb._on_failure()
        await cb._acquire()
        await cb._on_success()
        assert cb.failures == 0
        assert cb.state == State.CLOSED


class TestHalfOpenRecovery:
    @pytest.mark.asyncio
    async def test_success_closes(self):
        cb = CircuitBreaker(name="t", maxfail=1, reset_timeout=0)
        await cb._acquire()
        await cb._on_failure()
        await cb._acquire()  # transitions to HALF_OPEN
        await cb._on_success()
        assert cb.state == State.CLOSED
        assert cb.failures == 0

    @pytest.mark.asyncio
    async def test_failure_reopens(self):
        cb = CircuitBreaker(name="t", maxfail=1, reset_timeout=0)
        await cb._acquire()
        await cb._on_failure()
        await cb._acquire()
        await cb._on_failure()
        assert cb.state == State.OPEN


class TestHalfOpenQuota:
    @pytest.mark.asyncio
    async def test_exhausted_rejects(self):
        cb = CircuitBreaker(name="t", maxfail=1, reset_timeout=0, half_open_max_calls=1)
        await cb._acquire()
        await cb._on_failure()
        await cb._acquire()  # half-open
        with pytest.raises(CircuitBreakerOpenError):
            await cb._acquire()

    @pytest.mark.asyncio
    async def test_max_calls_gt_one(self):
        cb = CircuitBreaker(name="t", maxfail=1, reset_timeout=0, half_open_max_calls=2)
        await cb._acquire()
        await cb._on_failure()
        await cb._acquire()
        await cb._acquire()
        with pytest.raises(CircuitBreakerOpenError):
            await cb._acquire()


class TestTimeoutTransition:
    @pytest.mark.asyncio
    async def test_open_to_half_open_after_timeout(self):
        cb = CircuitBreaker(name="t", maxfail=1, reset_timeout=0.01)
        await cb._acquire()
        await cb._on_failure()
        await asyncio.sleep(0.02)
        await cb._acquire()
        assert cb.state == State.HALF_OPEN

    @pytest.mark.asyncio
    async def test_open_stays_before_timeout(self):
        cb = CircuitBreaker(name="t", maxfail=1, reset_timeout=60)
        await cb._acquire()
        await cb._on_failure()
        with pytest.raises(CircuitBreakerOpenError):
            await cb._acquire()
