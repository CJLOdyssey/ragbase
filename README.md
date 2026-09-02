# RagBase

基于检索增强生成（RAG）的知识库问答平台。上传私有文档，构建语义索引，获得带来源引用的精准问答。

[English](README_EN.md)

## 功能特性

- **RAG Pipeline** — Contextual Retrieval、Query Decomposition、HyDE，多策略混合检索（向量 + pg_trgm 词法 + RRF 融合）
- **知识库管理** — 文档上传、URL 导入（SSRF 逐跳防护）、语义切块、向量索引、Chunk 治理（增删改查/启禁用）、QA 批量导入
- **问答工作台** — 流式对话、会话管理、思维链展示、附件预览、版本分支
- **监控仪表盘** — ECharts 图表、健康评分、检索延迟分布、反馈审查
- **提示词管理** — 版本历史、启禁用状态、聊天 persona 绑定
- **检索日志** — 全链路检索追踪、延迟分析、Top Query 统计
- **安全** — RBAC 权限、JWT 认证、API Key Vault、SSRF 防护、速率限制

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12, FastAPI, SQLAlchemy (async), Celery, Redis |
| 数据库 | PostgreSQL + pgvector (HNSW) |
| 前端 | React 18, Vite 6, TypeScript, Ant Design 6, Tailwind CSS 4 |
| 图表 | ECharts 6 |
| 向量模型 | SiliconFlow BAAI/bge-m3 + bge-reranker-v2-m3 |
| 国际化 | i18next（中文 / 英文） |
| 质量 | ruff, mypy strict, pytest, vitest, ESLint |

## 快速开始

### Docker（推荐）

```bash
git clone https://github.com/CJLOdyssey/ragbase.git
cd ragbase
docker compose -f docker/compose.base.yml -f docker/compose.local.yml up -d
```

打开 http://localhost:5173

### 开发模式

```bash
# 后端
docker compose -f docker/compose.base.yml -f docker/compose.local.yml up -d postgres redis
make dev-backend

# 前端
cd frontend && npm install && npm run dev
```

打开 http://localhost:5174

## 测试

```bash
make test-backend        # 后端单元测试
make lint-backend        # Ruff lint
make typecheck-backend   # Mypy strict

cd frontend && npx vitest run   # 前端测试
```

## 项目结构

```
backend/src/
├── auth/          认证（JWT, RBAC）
├── rag/           RAG 管线（切块、嵌入、检索）
├── routers/       API 路由
├── repository/    数据访问层
├── tasks/         后台任务（Celery）
└── ...

frontend/src/
├── components/    页面组件（工作台、知识库、监控、提示词）
├── api/client/    API 客户端
├── stores/        状态管理
└── i18n/          国际化
```

## 许可证

[MIT](LICENSE)
