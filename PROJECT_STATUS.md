# RagBase 项目现状（2026-08-07）

## 一、项目定位

RAG 知识库问答平台：上传私有文档构建知识库，检索增强生成（RAG）提供带来源引用的问答。
独立项目、独立仓库。技术底座（auth/keys/sessions/runs/streaming/prompts/versions/rag）为自研裁剪体系。
规范驱动开发，规范见 `docs/SPEC.md`。

## 二、git 历史

```
feat/ragbase-migration ←（当前分支）
9be0350 docs: neutralize agent-studio references in specs
3d434e4 refactor: purge agent-studio/content-studio naming
dc7e322 fix: isolate tests to ragbase-redis, remove helm leftovers
6d6a092 fix: load canonical .env from backend root
107a080 feat: migrate content-studio to ragbase (repo baseline)
```

## 三、运行状态（当前）

| 服务 | 端口 | 状态 |
|---|---|---|
| 后端 | 8081 | health 200，连 `ragbase` 库（5433） |
| 前端 | 5174 | 200，proxy → 8081 |
| postgres | 5433 | `ragbase-db` 独立容器（pgvector/pg16，`ragbase` 库） |
| redis | 6380 | `ragbase-redis` 独立容器 |

标准启动命令（混合模式，开发推荐）：

```bash
docker compose -f docker/compose.base.yml -f docker/compose.local.yml up -d postgres redis
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5433/ragbase" make dev-backend
cd frontend && npm run dev
```

> 注意：DATABASE_URL 必须显式注入（run-backend.sh 不读 .env 兜底；opencode 沙箱会泄漏 `DATABASE_URL=file:...` 覆盖 .env）。

## 四、数据库与依赖环境

- ragbase → `ragbase` 库（**独立容器** `ragbase-db`：5433，pgvector/pg16；alembic head = `p9g3n002`）
- ragbase → `ragbase-redis`（**独立容器**：6380）
- 本项目一律使用 `ragbase-*` 独立容器（5433/6380）；共享实例（5432/6379）不在本项目范围，一律不得使用
- 项目边界：只操作本项目资源（`ragbase-*` 容器、`ragbase` 库、5433/6380）；共享实例的代码/数据/进程/配置一律不得修改

## 五、验证门

```bash
make lint-backend        # ruff
make typecheck-backend   # mypy strict
make test-backend-quick  # pytest
cd frontend && npx tsc --noEmit && npx eslint src/ && npx vitest run
```

## 六、配置文档

- `AGENTS.md`（项目根）：第一性原理审视规则 + 启动/环境/验证门
- `docs/SPEC.md`：项目规范（约束/功能/技术/工程/验收）
- 全局 `~/.config/opencode/AGENTS.md`：caveman/ponytail 等 skill 清单
