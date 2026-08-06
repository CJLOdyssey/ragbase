"""Flaky test detection, retry integration, and opt-in quarantine.

This module provides:
  - ``flaky_test``: decorator combining ``pytest.mark.flaky`` with pytest-rerunfailures.
  - ``--run-flaky``: CLI flag to opt into running quarantined flaky tests.
  - ``pytest_collection_modifyitems``: skips ``@pytest.mark.flaky`` tests by default.

Usage in test files:
  from tests.conftest_flaky import flaky_test

  @flaky_test(max_runs=5, min_passes=2)
  def test_something():
      ...

Quarantine policy (see ``tests/flaky/__init__.py``):
  1. Mark flaky tests with ``@flaky_test`` and file a ticket.
  2. CI runs them with ``--run-flaky`` to detect regressions without blocking builds.
  3. Fix the root cause within one sprint; remove ``@flaky_test`` after verification.
"""Flaky test detection and retry configuration.

Prefer pytest-rerunfailures (``--reruns 2`` in CI) over this decorator
for standard flaky test handling. This decorator is kept for edge cases
where per-test custom retry logic is needed.
"""
import asyncio
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import pytest

F = TypeVar("F", bound=Callable[..., Any])


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-flaky",
        action="store_true",
        default=False,
        help="Run tests marked as flaky (skipped by default).",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-flaky"):
        return
    skip_flaky = pytest.mark.skip(reason="flaky test — use --run-flaky to execute")
    for item in items:
        if item.get_closest_marker("flaky"):
            item.add_marker(skip_flaky)


def flaky_test(max_runs: int = 3, min_passes: int = 1, delay: float = 1):
    """Decorator to mark a test as flaky with automatic retry.

    Applies ``pytest.mark.flaky`` for CI-level retry (via pytest-rerunfailures)
    and wraps the test function with in-process retry logic as a fallback.

    Args:
        max_runs: Maximum total attempts.
        min_passes: Number of consecutive passes required to consider the test stable.
        delay: Seconds to wait between retries.
    """

    def decorator(func: F) -> F:
        marker = pytest.mark.flaky(reruns=max_runs - 1, reruns_delay=delay)

        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exception: BaseException | None = None
                passes = 0
                for attempt in range(max_runs):
                    try:
                        result = await func(*args, **kwargs)
                        passes += 1
                        if passes >= min_passes:
                            return result
                    except Exception as e:
                        last_exception = e
                        passes = 0
                        if attempt < max_runs - 1:
                            await asyncio.sleep(delay)
                if last_exception:
                    raise last_exception
                return None  # pragma: no cover — unreachable, kept for type checker

            result = marker(async_wrapper)
            return result  # type: ignore[return-value]

        else:

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exception: BaseException | None = None
                passes = 0
                for attempt in range(max_runs):
                    try:
                        result = func(*args, **kwargs)
                        passes += 1
                        if passes >= min_passes:
                            return result
                    except Exception as e:
                        last_exception = e
                        passes = 0
                        if attempt < max_runs - 1:
                            time.sleep(delay)
                if last_exception:
                    raise last_exception
                return None  # pragma: no cover — unreachable, kept for type checker

            result = marker(sync_wrapper)
            return result  # type: ignore[return-value]

def flaky_test(max_retries: int = 3, delay: float = 1):
    """Decorator to retry flaky tests (sync & async compatible)."""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                last_exception = None
                for attempt in range(max_retries):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_retries - 1:
                            await asyncio.sleep(delay)
                raise last_exception  # type: ignore[misc]
            return wrapper
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_retries - 1:
                            time.sleep(delay)
                raise last_exception  # type: ignore[misc]
            return wrapper
    return decorator
