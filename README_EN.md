# RagBase

A knowledge base Q&A platform powered by Retrieval-Augmented Generation (RAG). Upload private documents, build semantic indexes, and get precise answers with source citations.

[中文](README.md)

## Features

- **RAG Pipeline** — Contextual Retrieval, Query Decomposition, HyDE, hybrid search (vector + pg_trgm lexical + RRF fusion)
- **Knowledge Base** — Document upload, URL import with SSRF protection, semantic chunking, vector indexing, chunk governance (add/edit/delete/toggle), QA batch import
- **Chat Workbench** — Streaming conversations, session management, thinking chain display, attachment preview, version branching
- **Monitoring Dashboard** — ECharts charts, health scoring, retrieval latency distribution, feedback review
- **Prompt Management** — Version history, enable/disable, chat persona binding
- **Retrieval Logs** — Full-chain retrieval tracking, latency analysis, top query statistics
- **Security** — RBAC, JWT auth, API Key Vault, SSRF protection, rate limiting

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
make test-backend        # Backend unit tests
make lint-backend        # Ruff lint
make typecheck-backend   # Mypy strict

cd frontend && npx vitest run   # Frontend tests
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

## License

[MIT](LICENSE)
