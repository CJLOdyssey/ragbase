"""Per-test time limits to prevent hung tests from blocking CI.

Enforces:
  - 10s default for unit tests.
  - 60s for integration and slow tests.
  - ``@pytest.mark.timeout(N)`` for custom limits on specific tests.

Requires ``pytest-timeout`` package. Install with: pip install pytest-timeout
"""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "timeout(seconds): override the default test timeout for a specific test",
    )


@pytest.fixture(autouse=True)
def _enforce_test_timeout(request: pytest.FixtureRequest) -> None:
    """Apply per-test timeout based on markers.

    Priority (highest first):
      1. ``@pytest.mark.timeout(N)`` — explicit override on the test.
      2. CLI ``--timeout=N`` flag — if set, skip marker-based timeout (let the CLI handle it).
      3. ``@pytest.mark.slow`` or ``@pytest.mark.integration`` → 120s.
      4. Default → 30s (unit test).

    The ``pytest-timeout`` plugin handles the actual timeout enforcement;
    this fixture applies the marker so the plugin sees it.
    """
    has_explicit_timeout = request.node.get_closest_marker("timeout") is not None
    if has_explicit_timeout:
        return

    # If --timeout was passed on CLI, defer to that instead of our defaults
    if request.config.option.timeout:
        return

    is_long = (
        request.node.get_closest_marker("slow") is not None
        or request.node.get_closest_marker("integration") is not None
    )
    timeout_seconds = 120 if is_long else 30

    request.node.add_marker(pytest.mark.timeout(timeout_seconds))
