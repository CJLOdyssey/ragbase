"""Async circuit breaker for protecting downstream service calls (LLM, Celery, etc.).

Simple three-state machine: closed → open → half-open → closed.
Tracks consecutive failures in memory; no external dependencies.
"""

from __future__ import annotations

import asyncio
import time
from enum import Enum
from typing import Any


class State(Enum):
    CLOSED = "closed"          # Normal operation
    OPEN = "open"              # Reject all calls
    HALF_OPEN = "half_open"    # Allow one test call


class CircuitBreakerOpenError(Exception):
    """Raised when a call is rejected because the circuit is open."""


class CircuitBreaker:
    """Async circuit breaker with configurable thresholds.

    Usage::

        llm_cb = CircuitBreaker(name="llm_api", maxfail=5, reset_timeout=30)

        async with llm_cb:
            result = await call_llm_api()

    The circuit opens after `maxfail` consecutive failures.
    After `reset_timeout` seconds in OPEN, transitions to HALF_OPEN.
    One successful call in HALF_OPEN transitions back to CLOSED.
    Any failure in HALF_OPEN re-opens the circuit.
    """

    def __init__(
        self,
        name: str,
        maxfail: int = 5,
        reset_timeout: float = 60.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self.name = name
        self.maxfail = maxfail
        self.reset_timeout = reset_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = State.CLOSED
        self._failures: int = 0
        self._last_failure: float = 0.0
        self._opened_at: float = 0.0
        self._half_open_calls: int = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> State:
        return self._state

    @property
    def failures(self) -> int:
        return self._failures

    async def _transition(self) -> None:
        """Evaluate state transition based on current state and elapsed time.

        Raises CircuitBreakerOpenError when the circuit should reject calls
        (e.g. exhausted half-open quota).
        """
        now = time.time()

        if self._state == State.OPEN:
            if now - self._opened_at >= self.reset_timeout:
                self._state = State.HALF_OPEN
                self._half_open_calls = 0

        elif self._state == State.HALF_OPEN and self._half_open_calls >= self.half_open_max_calls:
            raise CircuitBreakerOpenError(
                f"Circuit '{self.name}' is HALF_OPEN — "
                f"{self._half_open_calls} test calls already in flight"
            )

    async def _on_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            if self._state == State.HALF_OPEN:
                self._state = State.CLOSED
                self._failures = 0
                self._half_open_calls = 0
            elif self._state == State.CLOSED:
                self._failures = 0

    async def _on_failure(self) -> None:
        """Record a failed call."""
        async with self._lock:
            now = time.time()
            self._failures += 1
            self._last_failure = now

            if self._state == State.HALF_OPEN or self._state == State.CLOSED and self._failures >= self.maxfail:
                self._state = State.OPEN
                self._opened_at = now

    async def _acquire(self) -> None:
        """Try to acquire permission to make a call. Raises CircuitBreakerOpenError if denied."""
        async with self._lock:
            await self._transition()

            if self._state == State.OPEN:
                elapsed = time.time() - self._opened_at
                remaining = max(0.0, self.reset_timeout - elapsed)
                raise CircuitBreakerOpenError(
                    f"Circuit '{self.name}' is OPEN — {self._failures} failures, "
                    f"retry in {remaining:.0f}s"
                )

            if self._state == State.HALF_OPEN:
                self._half_open_calls += 1

    def __call__(self, func: Any) -> Any:
        """Decorator to wrap an async callable with circuit breaker protection.

        Usage::

            cb = CircuitBreaker(name="llm", maxfail=5, reset_timeout=30)

            @cb
            async def call_llm(prompt: str) -> str:
                return await api.chat(prompt)

        Raises:
            CircuitBreakerOpenError: when the circuit is open and the call is rejected.
        """
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            await self._acquire()
            try:
                result = await func(*args, **kwargs)
            except CircuitBreakerOpenError:
                raise
            except Exception:
                await self._on_failure()
                raise
            else:
                await self._on_success()
            return result

        return wrapper

    def status(self) -> dict[str, Any]:
        """Return current status for monitoring/debug endpoints."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failures": self._failures,
            "maxfail": self.maxfail,
            "reset_timeout": self.reset_timeout,
            "last_failure": self._last_failure,
        }


# ── Shared circuit breakers ──────────────────────────────────────────────────

# LLM API circuit breaker — protects against cascading failures when
# the LLM provider is down or returning errors. Shared by all graph engines.
# Configurable via env vars: LLM_CB_MAXFAIL (default 5), LLM_CB_RESET (default 60s).
import os as _os

_llm_maxfail = int(_os.environ.get("LLM_CB_MAXFAIL", "5"))
_llm_reset = float(_os.environ.get("LLM_CB_RESET", "60"))

llm_circuit = CircuitBreaker(
    name="llm_api",
    maxfail=_llm_maxfail,
    reset_timeout=_llm_reset,
)
