# RagBase

基于检索增强生成（RAG）的知识库问答平台。上传私有文档，构建语义索引，获得带来源引用的精准问答。

## Features

- **RAG Pipeline** — Contextual Retrieval、Query Decomposition、HyDE，多策略混合检索（向量 + pg_trgm 词法 + RRF 融合）
- **知识库管理** — 文档上传、URL 导入（SSRF 逐跳防护）、语义切块、向量索引、Chunk 治理（增删改查/启禁用）、QA 批量导入
- **问答工作台** — 流式对话、会话管理、思维链展示、附件预览、版本分支
- **监控仪表盘** — ECharts 图表、健康评分、检索延迟分布、反馈审查
- **提示词管理** — 版本历史、启禁用状态、聊天 persona 绑定
- **检索日志** — 全链路检索追踪、延迟分析、Top Query 统计
- **安全** — RBAC 权限、JWT 认证、API Key Vault、SSRF 防护、速率限制

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy (async), Celery, Redis |
| Database | PostgreSQL + pgvector (HNSW) |
| Frontend | React 18, Vite 6, TypeScript, Ant Design 6, Tailwind CSS 4 |
| Charts | ECharts 6 |
| Embedding | SiliconFlow BAAI/bge-m3 + bge-reranker-v2-m3 |
| i18n | i18next (zh-CN / en-US) |
| Quality | ruff, mypy strict, pytest, vitest, ESLint |

## Quick Start

### Docker (recommended)

```bash
git clone https://github.com/CJLOdyssey/ragbase.git
cd ragbase
docker compose -f docker/compose.base.yml -f docker/compose.local.yml up -d
```

Open http://localhost:5173

### Development

```bash
# Backend
docker compose -f docker/compose.base.yml -f docker/compose.local.yml up -d postgres redis
make dev-backend

# Frontend
cd frontend && npm install && npm run dev
```

Open http://localhost:5174

## Testing

```bash
make test-backend     # Backend unit tests
make lint-backend     # Ruff lint
make typecheck-backend  # Mypy strict

cd frontend && npx vitest run  # Frontend tests
```

## Project Structure

```
backend/src/
├── auth/          Authentication (JWT, RBAC)
├── rag/           RAG pipeline (chunking, embedding, retrieval)
├── routers/       API routes
├── repository/    Data access layer
├── tasks/         Background tasks (Celery)
└── ...

frontend/src/
├── components/    UI (studio, assets, knowledge-base, monitoring, prompts)
├── api/client/    API client
├── stores/        State management
└── i18n/          Internationalization
```

## Contributing

See [AGENTS.md](AGENTS.md) for development conventions.

## License

[MIT](LICENSE)
