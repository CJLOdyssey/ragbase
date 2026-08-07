# RagBase — RAG 知识库问答平台

上传私有文档构建知识库，基于检索增强生成（RAG）提供带来源引用的问答：文档上传 → 语义切块 → 向量索引 → 混合检索 → 生成。

## 项目定位

独立项目、独立仓库。技术底座（auth/keys/sessions/runs/streaming/prompts/versions/rag）为自研裁剪体系，业务领域为文档知识库问答。规范见 [docs/SPEC.md](docs/SPEC.md)（规范驱动开发）。

## 技术栈

- 后端：Python 3.12 + FastAPI + SQLAlchemy(async) + PostgreSQL(pgvector) + Redis + Celery
- 前端：React 18 + Vite + TypeScript + Ant Design
- RAG：DashScope text-embedding-v3 + pgvector HNSW + 语义切块
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
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5433/ragbase" make dev-backend
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
├── rag/           # RAG 管线（切块/嵌入/向量存储/检索）
├── repository/    # 数据访问层
├── routers/       # API 路由（auth/keys/sessions/runs/assets/prompts/...）
├── services/      # 业务服务（run_service 等）
├── streaming/     # SSE/流式输出
└── tasks/         # 后台任务管线

frontend/src/
├── api/client/    # API 客户端
├── components/    # 页面组件（studio 工作台/assets 知识库/auth/input/settings）
└── i18n/          # 国际化
```

## 核心数据流

1. **知识库**：文档上传（/api/assets）→ 语义切块 → embedding → pgvector 存储
2. **问答**：用户提问 → 向量检索相关片段 → 上下文注入 → 流式生成 → 会话/消息持久化

## 默认账号

- 管理员：`admin@example.com` / `admin123`（生产环境必须通过 `SEED_ADMIN_PASSWORD` 环境变量修改）

## License

MIT
