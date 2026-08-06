"""E2E-only fixtures. 限流清理仅在 e2e 目录生效，避免单元测试被 docker exec 拖慢。"""

import subprocess

import pytest


def _clear_rate_limits() -> None:
    try:
        out = subprocess.run(
            ["docker", "exec", "agent-studio-redis", "redis-cli", "-n", "1", "KEYS", "ratelimit:*"],
            capture_output=True, text=True, timeout=5,
        )
        if out.stdout.strip():
            keys = out.stdout.strip().split("\n")
            subprocess.run(
                ["docker", "exec", "agent-studio-redis", "redis-cli", "-n", "1", "DEL"] + keys,
                capture_output=True, timeout=5,
            )
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _fresh_rate_limit() -> None:
    _clear_rate_limits()
