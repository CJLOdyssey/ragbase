"""E2E-only fixtures. 限流清理仅在 e2e 目录生效，避免单元测试被 docker exec 拖慢。"""

import subprocess

import pytest


def _clear_rate_limits() -> None:
    # 实际限流 key 是 auth:* 命名空间（auth/send-register-code 等），
    # 历史只清 ratelimit:* 导致旧 key 残留 → send-code 永久 429 → register 流程
    # 永远走不通（token 拿不到 → 依赖认证的测试全 401）。
    try:
        out = subprocess.run(
            ["docker", "exec", "ragbase-redis", "redis-cli", "-n", "0", "KEYS", "*"],
            capture_output=True, text=True, timeout=5,
        )
        if out.stdout.strip():
            keys = out.stdout.strip().split("\n")
            subprocess.run(
                ["docker", "exec", "ragbase-redis", "redis-cli", "-n", "0", "DEL"] + keys,
                capture_output=True, timeout=5,
            )
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _fresh_rate_limit() -> None:
    _clear_rate_limits()
