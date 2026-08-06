# ContentStudio — 内容创作助手

输入主题/素材，输出可直接发布的图文内容：小红书笔记、公众号文章、短视频脚本、营销文案，支持 AI 配图合成卡片。

## 与 agent-studio 的关系

独立项目、独立仓库。技术底座（auth/keys/sessions/runs/streaming/prompts/versions/rag）从 [agent-studio](../agent-studio) 裁剪而来，业务领域刻意错开（内容创作 vs 软件虚拟团队）。规范见 [docs/SPEC.md](docs/SPEC.md)（规范驱动开发）。

## 技术栈

- 后端：Python 3.12 + FastAPI + SQLAlchemy(async) + PostgreSQL + Redis + Celery
- 前端：React 18 + Vite + TypeScript + Ant Design
- RAG：DashScope text-embedding-v3（品牌风格库）
- 质量：ruff + mypy strict + pytest（unit/integration/e2e 分层）+ vitest

## 快速开始

### 方式一：全容器（Docker Compose）

```bash
docker compose -f docker/compose.base.yml -f docker/compose.local.yml up -d
```

前端 `http://localhost:5173`，后端 `http://localhost:8080`。

### 方式二：混合模式（开发推荐）

```bash
docker compose -f docker/compose.base.yml -f docker/compose.local.yml up -d postgres redis
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/backend" make dev-backend
cd frontend && npm run dev
```

### 测试

```bash
make test-backend    # 后端（排除 integration/benchmark）
make test-frontend   # 前端 vitest
```

## 目录结构

```
backend/src/
├── auth/          # 认证（登录/注册/JWT/RBAC）
├── core/          # 配置/中间件/错误码/基础设施
├── graph/         # 单 Agent 生成引擎
├── rag/           # RAG 管线（品牌风格库）
├── repository/    # 数据访问层
├── routers/       # API 路由（auth/keys/sessions/runs/prompts/...）
├── services/      # 业务服务（run_service 等）
├── streaming/     # SSE/流式输出
└── tasks/         # 后台任务管线

frontend/src/
├── api/client/    # API 客户端
├── components/    # 页面组件（content 创作台/auth/input/shared）
└── i18n/          # 国际化
```

## 已裁剪内容

从 agent-studio 裁剪掉：多 Agent 编排（teams/agents/agent_configs）、工具生态（tools/mcps/skills）、工作流引擎（workflow）、监控运维（admin）。保留：认证、会话、运行管线、提示词模板、版本历史、RAG。

## 默认账号

- 管理员：`admin@example.com` / `admin123`（生产环境必须通过 `SEED_ADMIN_PASSWORD` 环境变量修改）

## License

MIT（同 agent-studio）
