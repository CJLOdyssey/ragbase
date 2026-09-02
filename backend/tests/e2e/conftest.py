"""E2E-only fixtures. 限流清理仅在 e2e 目录生效，避免单元测试被 docker exec 拖慢。"""

import subprocess

import pytest

#: 后端 REDIS_URL 指向 db 1（redis://localhost:6380/1，见 systemd 环境）——
#: auth:verify:* 验证码与限流 key 都在 db 1，历史误用 db 0 导致读不到验证码。
_REDIS_DB = "1"


def _clear_rate_limits() -> None:
    # 实际限流 key 是 auth:* 命名空间（auth/send-register-code 等），
    # 历史只清 ratelimit:* 导致旧 key 残留 → send-code 永久 429 → register 流程
    # 永远走不通（token 拿不到 → 依赖认证的测试全 401）。
    try:
        out = subprocess.run(
            ["docker", "exec", "ragbase-redis", "redis-cli", "-n", _REDIS_DB, "KEYS", "*"],
            capture_output=True, text=True, timeout=5,
        )
        if out.stdout.strip():
            keys = out.stdout.strip().split("\n")
            subprocess.run(
                ["docker", "exec", "ragbase-redis", "redis-cli", "-n", _REDIS_DB, "DEL"] + keys,
                capture_output=True, timeout=5,
            )
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _fresh_rate_limit() -> None:
    _clear_rate_limits()
