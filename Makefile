.PHONY: test test-backend test-frontend lint-backend typecheck-backend lint-frontend coverage e2e-env test-e2e test-benchmark

# 统一排除规则：integration 需要真后端+docker (有 @pytest.mark.integration)，
# benchmark 是性能测试（locust 覆盖）。与 CI (pytest-split) 共用同一 marker 约定，
# 不再维护目录黑名单清单。
TEST_EXCLUDE=-m "not integration and not benchmark"

test: test-backend test-frontend

test-backend:
	pytest --cov=backend $(TEST_EXCLUDE)

test-backend-quick:
	pytest -q -x --tb=short $(TEST_EXCLUDE)

## 增量测试（pytest-testmon）：只跑受代码变更影响的测试。
## 注意：testmon 不支持 xdist 并行（-n 0），且需先跑一次全量基线：
##   make test-backend-incremental-baseline   # 首次/大改动后重建 .testmondata
## 之后每次改动代码，跑 make test-backend-incremental 即可。
test-backend-incremental:
	pytest -n 0 $(TEST_EXCLUDE) --testmon --cov=backend

test-backend-incremental-baseline:
	pytest -n 0 $(TEST_EXCLUDE) --testmon --testmon-new-first --cov=backend

test-frontend:
	cd frontend && npx vitest run --coverage.enabled

lint-backend:
	ruff check backend/

typecheck-backend:
	mypy backend/src --strict --explicit-package-bases

lint-frontend:
	cd frontend && npx eslint src/

format-backend:
	ruff format backend/

coverage:
	pytest --cov=backend --cov-report=term-missing $(TEST_EXCLUDE)

## E2E 测试环境一键拉起（postgres + redis，随后 make dev-backend 起后端）
e2e-env:
	bash scripts/dev/e2e-env.sh

## 跑 API 级 E2E（需要 e2e-env + 后端已启动在 8082）
test-e2e:
	pytest backend/tests/e2e/ -m integration

## 性能基准（需要活后端，默认 8082 E2E 后端）。
## 压测会并发打满连接池 — 后端需配大池（REDIS_POOL_SIZE/DATABASE_POOL_SIZE，
## 参考下方 8082 启动示例）。-n 0 强制单进程：xdist 多 worker 并发压测会
## 打爆单 uvicorn（累计 1200+ 并发 → 503/超时）。
## 8082 启动示例：
##   PORT=8082 REDIS_POOL_SIZE=256 DATABASE_POOL_SIZE=256 bash scripts/dev/run-backend.sh
test-benchmark:
	E2E_BASE_URL=http://localhost:8082 \
	BENCH_BASE_URL=http://localhost:8082 BENCH_WS_URL=ws://localhost:8082 \
	pytest backend/tests/benchmark/ -m benchmark -n 0

.PHONY: dev-backend dev-backend-reload dev-backend-logs restart-backend health

## Start backend (自动杀旧进程 + 端口检测, 默认不带 --reload)
dev-backend:
	@bash scripts/dev/run-backend.sh

## Restart backend — kill all instances, then start fresh (alias of dev-backend)
restart-backend:
	@bash scripts/dev/run-backend.sh

## Start backend with hot-reload (有风险: 可能触发子进程卡死)
dev-backend-reload:
	RELOAD=1 bash scripts/dev/run-backend.sh

## Tail backend logs
dev-backend-logs:
	tail -f /tmp/ragbase-backend.log

## Run health check against backend
health:
	python scripts/dev/health.py --port ${PORT:-8080} --check-orphans

# ── 混合模式: 后端(systemd) + 前端(tmux) ──────────────────────────
.PHONY: up down restart status logs frontend

## 一键启动后端 + 前端
up:
	bash scripts/dev/ragbase.sh start

## 一键停止
down:
	bash scripts/dev/ragbase.sh stop

## 一键重启
restart:
	bash scripts/dev/ragbase.sh restart

## 查看服务状态
status:
	bash scripts/dev/ragbase.sh status

## 查看后端日志 (Ctrl+C 退出)
logs:
	bash scripts/dev/ragbase.sh logs

## attach 到前端 tmux session (Ctrl+B D 退出)
frontend:
	bash scripts/dev/ragbase.sh frontend
