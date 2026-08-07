# RagBase 项目现状（2026-08-07）

## 一、项目定位

RAG 知识库问答平台：上传私有文档构建知识库，检索增强生成（RAG）提供带来源引用的问答。
由前身项目（内容创作助手）迁移而来：内容生成/图文合成层已移除，知识库底座保留并成为核心。
独立项目、独立仓库。技术底座（auth/keys/sessions/runs/streaming/prompts/versions/rag）为自研裁剪体系。
规范驱动开发，规范见 `docs/SPEC.md`。

## 二、git 历史

```
feat/ragbase-migration ←（当前）
6d6a092 fix: load canonical .env from backend root instead of src (dedupe env files)
107a080 feat: migrate content-studio to ragbase — rename stack, drop content-generation layer, add p9g3n002 migration
88b06e7 wip: settings/studio workspace baseline（迁移前未提交变更入库）
44848df fix: settings keys query waits for auth
...（此前 36 个 commit：内容创作时代）
579e625 feat: init ContentStudio from agent-studio skeleton
```

## 三、迁移内容（ragbase-migration 分支）

### 已删除（内容创作层）
- 后端：`services/generation_service.py`、`image_service.py`、`structured.py`、`routers/generation.py`、`repository/compose_templates.py`
- 后端测试 ×6：test_generation_service/test_image_service/test_structured/test_generation_routes/test_compose_templates_repo/test_generation_models
- 前端：`components/content/`（5 组件+3 测试）、`components/history/`（+测试）、`api/client/generations.ts`、`composeTemplates.ts`、`types/generation.ts`、i18n content/history 命名空间 ×2 语言
- 路由：`/api/generations*`、`/api/compose-templates`、前端 `/history`
- DB：`compose_templates` 表 + `project_runs` 的 5 列（content_type/generation_mode/topic/result_json/template_id）—— 迁移 `p9g3n002`

### 保留（底座 + 知识库）
- 后端：auth/keys/sessions/runs/streaming/prompts/versions/attachments/rag/checkpoint/graph/broker/observability/tasks
- `routers/assets.py`（知识库 CRUD + RAG index，用户级隔离）+ `orm/infra.AssetDB`
- 前端：studio 工作台/settings/input/shared/stores/auth

### 改名
- 项目名 content-studio → **ragbase**（容器 `ragbase-*`、镜像、数据库 `ragbase`、API 标题 RagBase API、前端 title/package name、scripts PIDFILE）
- 数据库/容器命名空间隔离保持不变（5433/6380 独立容器）

## 四、运行状态（当前）

| 服务 | 端口 | 状态 |
|---|---|---|
| 后端 | 8081 | health 200，连 `ragbase` 库（5433） |
| 前端 | 5174 | 200，proxy → 8081 |
| postgres | 5433 | `ragbase-db` 独立容器（pgvector/pg16） |
| redis | 6380 | `ragbase-redis` 独立容器 |

标准启动命令（混合模式，开发推荐）：

```bash
docker compose -f docker/compose.base.yml -f docker/compose.local.yml up -d postgres redis
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5433/ragbase" make dev-backend
cd frontend && npm run dev
```

> 注意：DATABASE_URL 必须显式注入（run-backend.sh 不读 .env 兜底；opencode 沙箱会泄漏 `DATABASE_URL=file:...` 覆盖 .env）。

## 五、数据库隔离

- ragbase → `ragbase` 库（**独立容器** `ragbase-db`：5433，pgvector/pg16；alembic_version 目标 = `p9g3n002`）
- ragbase → `ragbase-redis`（**独立容器**：6380）
- agent-studio → `backend` 库（共享实例 5432/6379，**不再触碰**）
- 已授权范围：不得修改 agent-studio 的代码/数据/进程/配置

## 六、迁移遗留（已完成）

| 项 | 内容 | 状态 |
|---|---|---|
| 迁移执行 | DB `p9g3n002`（drop compose_templates + 5 列）在真实库执行 | ✅ 2026-08-07：旧容器 `content-studio-db/redis` 移除，`ragbase-db`(5433)/`ragbase-redis`(6380) 重建，alembic upgrade head 全链跑通，`alembic current = p9g3n002 (head)`；旧库备份 `/tmp/opencode/ragbase-backup/content_studio_20260807.dump` |
| 现有数据 | content_studio 旧库数据不迁移（新库 ragbase 从迁移链全新构建） | ✅ 已执行（旧库数据废弃） |
| 目录改名 | 项目目录 `content-studio` → `ragbase` | ✅ 已完成（git mv 入库，提交 107a080） |
| env 文件合并 | `backend/src/.env` 与 `backend/.env` 重复 | ✅ 2026-08-07：规范位置定为 `backend/.env`（应用根），config.py/database.py 加载路径修正（提交 6d6a092），`backend/src/.env` 已删除 |

## 七、配置文档

- `AGENTS.md`（项目根）：第一性原理审视规则 + 启动/环境/验证门
- `docs/SPEC.md`：项目规范（约束/功能/技术/工程/验收）
- 全局 `~/.config/opencode/AGENTS.md`：caveman/ponytail 等 skill 清单

## 八、验证门

```bash
make lint-backend        # ruff
make typecheck-backend   # mypy strict
make test-backend-quick  # pytest
cd frontend && npx tsc --noEmit && npx eslint src/ && npx vitest run
```
