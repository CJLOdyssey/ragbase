#!/usr/bin/env bash
# 一键拉起 E2E 测试环境（postgres + redis）。
# 用法: make e2e-env   或   bash scripts/dev/e2e-env.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
    echo "❌ 未找到 docker，无法启动测试环境" >&2
    exit 1
fi

echo "▶ 启动 postgres + redis (docker/compose.local.yml)..."
docker compose -f docker/compose.base.yml -f docker/compose.local.yml up -d postgres redis

for c in ragbase-db ragbase-redis; do
    if [ -z "$(docker ps -q -f name="$c" -f status=running)" ]; then
        echo "❌ $c 未运行" >&2
        exit 1
    fi
done

echo "✅ E2E 环境就绪：postgres=5433, redis=6380"
echo "   下一步:"
echo "     PORT=8082 make dev-backend   # 启动后端 (端口 8082, E2E 测试目标)"
echo "     make test-e2e           # 运行 API 级 E2E 测试"
