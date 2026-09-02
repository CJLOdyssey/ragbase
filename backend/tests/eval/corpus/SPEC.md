# RagBase 项目规范（SPEC）

> **规范驱动开发**：所有开发（新增/修改/裁剪）必须遵循本文档。规范与代码冲突时以本文档为准并先更新本文档。

**项目定位**：RAG 知识库问答平台——上传私有文档构建知识库，基于检索增强生成（RAG）提供带来源引用的问答。独立项目、独立仓库（`projects/ragbase`），技术底座（auth/keys/sessions/runs/streaming/prompts/versions/rag）为自研裁剪体系，业务领域为文档知识库问答。

---

## 一、全局约束（Global Constraints）

### 1.1 技术栈版本

| 层 | 技术 | 版本约束 |
|---|---|---|
| 后端语言 | Python | >= 3.11 |
| 后端框架 | FastAPI + SQLAlchemy(async) + asyncpg | 沿用既有锁定版本 |
| 任务队列 | Celery + Redis | 沿用 |
| 前端 | React + Vite + TypeScript | Node 22，沿用既有 |
| 前端 UI | Ant Design + Tailwind（workstation 部分）+ 自研组件 | 沿用 |
| 数据库 | PostgreSQL + pgvector | 沿用 |
| 向量/embedding | DashScope text-embedding-v3（RAG） | 沿用 rag 五件套 |

### 1.2 代码规范

- ruff：line-length=120，select E/F/I/N/W/UP/B/SIM（从 pyproject.toml 继承，禁止放宽）
- mypy：strict 模式 + pydantic 插件（从 pyproject.toml 继承）
- 前端：tsc --noEmit 必须零错误；eslint 零 error
- 单文件 ≤400 行，超限拆分（全局 AGENTS.md 约束）
- 禁止大段 if-else/嵌套分支：早返回、策略模式、字典映射、状态机

### 1.3 命名规范

| 项 | 规则 |
|---|---|
| 后端模块 | 小写下划线（如 `routers/assets.py`） |
| 路由前缀 | `/api/<资源名>` 复数（沿用现有） |
| 数据库名 | `ragbase`（独立容器 5433，pgvector/pg16） |
| 前端组件 | PascalCase，页面组件 `Page` 后缀 |
| i18n key | 点分命名空间，全部走 t()，禁止硬编码中文文案 |

### 1.4 依赖约束

- 只允许引入既有已验证依赖（声明在 `pyproject.toml` `[project].dependencies`，锁定于 `uv.lock`，单一来源）
- 新增依赖必须评审（LLM 直连 SDK 用 openai/anthropic/dashscope）
- **禁止 langchain 高层 Agent 抽象**（`langchain.agents` / AgentExecutor / 预置 Chain）；graph 引擎为自研编排，但允许基于 langgraph StateGraph 底层 + `langchain_core` Message 类型 + `langchain_openai.ChatOpenAI` 构建（见 `graph/`）
- RAG 用 DashScope text-embedding-v3，不新增向量库替代方案（pgvector 已锁定）

### 1.5 安全

- 所有业务 API 必须过 AuthMiddleware（沿用）
- API Key 走 vault（沿用 keys.py 的 key_id 解析模式，服务端解密，永不暴露给前端）
- 上传文件大小限制沿用 RequestSizeLimitMiddleware
- 用户输入做长度校验（沿用 max_requirement_length 模式）

---

## 二、功能细节规范

### 2.1 页面结构

| 页面 | 路由 | 职责 |
|---|---|---|
| 问答工作台 | `/` | 主流程（提问 → RAG 检索 → 流式回答），会话列表在左栏 |
| 知识库 | `/assets` | 文档上传/列表/重命名/删除/索引（RAG 输入侧） |
| 设置 | `/settings` | API Key、模型、提示词模板、账号 |

### 2.2 问答工作台交互细节

1. **会话流**：左栏会话列表（复用 sessions），主区消息流（复用 chatStore/WS 流式），输入框常驻
2. **生成中状态**：按钮变"停止"，WebSocket 流式展示（stream/thinking/result/error 事件）
3. **生成失败**：显示错误 + 重试按钮，不丢已输入内容
4. **继续生成**：复用 run_continue 语义（同会话上下文续写）
5. **编辑/分支/版本**：编辑历史消息 = 创建新分支（新 run，`parent_run_id` 指向被编辑消息所在 run）。
   分页按钮在兄弟版本间切换；切换后视图只显示选中 turn（用户消息 + 对应回答），
   该分支点之后的后续轮次不显示但留存数据库。继续发送 = 新 run 挂在当前选中 run 下。
   RAG 上下文入口 = 当前选中 turn 的用户消息（沿 parent 链回溯注入上下文）。

### 2.3 知识库细节

1. 上传：文档（pdf/txt/md ≤20MB），用户级隔离（assets.user_id）
2. 索引：语义切块 → embedding → pgvector 存储（POST /api/assets/{id}/index）
3. 列表：名称 + 类型 + 大小 + 索引状态（indexed）
4. 删除：确认弹窗；同步清理存储文件

### 2.4 设置页细节

1. API Key 管理（复用 keys）：LLM key + embedding key 分 provider 展示
2. 模型选择（复用 models）
3. 提示词模板（复用 prompts）
4. 账号（复用 auth）：资料/改密/登出

### 2.5 密钥能力体系（统一分类）

- `user_api_keys.capabilities`：JSON 数组，取值 ∈ {llm, embedding, rerank, speech2text, tts, moderation, image, tool}（对齐 Dify ModelType + Tool 插件类别）。真源为 backend `domain/capabilities.py`（8 类）。
- 图像生成（image）为独立类型：图像生成模型（如 SiliconFlow text-to-image/image-to-image/text-to-video）映射为 `image`，不归入 tool（图像生成 provider 与 tool provider 分开跟踪，见 `streaming/image_generation.py`、`services/run_service.py` 的 `model_types == "image"` 分支）。
- 自定义供应商无条件出现在所有分组（`custom_llm`/`custom_embedding`/`custom_rerank`/`custom_speech2text`/`custom_tts`/`custom_moderation`/`custom_image`/`custom_tool`）。
- 分组标签 zh-CN：LLM / 嵌入(Embedding) / 重排序(Rerank) / 语音转文字 / 文字转语音 / 内容审核(Moderation) / 图像(Image) / Tool。
- 分类规则唯一真源：backend `domain/capabilities.py`、frontend `utils/providerCategories.ts`。
- `/api/models` 返回 `ModelInfo.type`（8 能力枚举，未知默认 llm），前端模型 tab 按 type 分组。
- 模型类型真源化：拉取模型时按供应商 `sub_type` 分类（SiliconFlow chat/embedding/reranker/text-to-image/image-to-image/speech-to-text/text-to-video，映射 8 能力），存入 `user_api_keys.model_types`（JSONB map，可空）；`/api/models` 优先读存储类型，名称启发式仅兜底；添加/编辑 key 表单支持手动改每模型类型。

---

## 三、技术规范

### 3.1 后端目录（目标态）

```
backend/src/
├── auth/            # 保留（全量）
├── broker/          # 保留（Redis 缓冲/订阅）
├── checkpoint/      # 保留
├── core/            # 保留（config/app/error_codes/infra）
├── graph/           # 保留（SingleAgentGraph 为主）
├── observability/   # 保留（日志/指标/审计）
├── orm/             # 保留 users/refresh_tokens/roles/user_roles/
│                    #      user_api_keys/key_usage_logs/sessions/project_runs/
│                    #      chat_messages/memory_entries/prompts/versions/
│                    #      assets/attachments/audit_logs
├── rag/             # 保留（RAG 管线核心：切块/嵌入/向量存储/检索）
├── repository/      # 保留与 orm 对应的 crud
├── routers/         # 保留：auth/keys/models/prompts/providers/runs/run_continue/
│                    #      sessions/attachments/assets/versions
├── services/        # 保留：run_service/session_service/email_service/text_utils
├── streaming/       # 保留
├── tasks/           # 保留：agent_pipeline（单 agent 路径）
└── uploads/         # 保留（assets/attachments 存储）
```

### 3.2 RAG 管线设计

```
上传文档（POST /api/assets）
  ├─ 校验类型/大小（pdf/txt/md ≤20MB）
  ├─ 存储文件（uploads/assets/）
  ├─ 语义切块（rag_chunking.semantic_chunk）
  ├─ embedding（DashScope text-embedding-v3，1024 维）
  ├─ pgvector 存储（rag_store.PgVectorStore，HNSW）
  └─ assets.indexed = true

问答（runs + streaming）
  ├─ 用户提问 → 创建 run
  ├─ rag_pipeline.retrieve_context 向量检索相关片段
  ├─ 上下文注入 → LLM 流式调用 → WebSocket 推送
  └─ 结果持久化（chat_messages）
```

### 3.3 API 设计（现有端点）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/attachments` | 会话级附件上传 |
| GET/POST/PUT/DELETE | `/api/assets` | 知识库文档 CRUD |
| POST | `/api/assets/{asset_id}/index` | 建 RAG 索引 |
| GET/POST | `/api/runs`、`/api/sessions` | 运行/会话（沿用） |
| POST | `/api/runs/{run_id}/continue` | 继续生成（沿用） |

> 编辑/分支不新增端点：PUT /api/runs/{run_id}/answer-versions（版本数组持久化）随分支树重构废弃删除；parent_run_id 透出（已存在于 sessions detail）。

### 3.4 数据表

| 表 | 说明 |
|---|---|
| `assets` | id, user_id, name, asset_type(document), size_bytes, storage_path, usage_count, indexed, created_at, updated_at — 用户级知识库文档 |
| `project_runs` | 通用 run（requirement/pm_document/code/review/status/parent_run_id），generation 列已删除——parent_run_id 为树指针：编辑分支与续聊统一为树节点，视图 = 根→选中节点路径；chat_messages.versions/thinking_versions 列废弃不再写入 |
| 其余 | 沿用裁剪底座表（auth/keys/sessions/messages/memory/prompts/versions/attachments/日志） |

### 3.5 前端目录（目标态）

```
frontend/src/
├── components/
│   ├── auth/          # 保留（登录/注册）
│   ├── studio/        # 保留：问答工作台（RagBaseWorkstation/HomeScreen/MessagesPanel）
│   ├── input/         # 保留（输入工具栏/模型选择/附件）
│   ├── shared/        # 保留（EmptyState 等通用）
│   ├── assets/        # 保留：知识库（AssetsPage）
│   └── settings/      # 保留：设置（API Key/模型）
├── api/client/        # 裁剪后：auth/keys/models/prompts/providers/runs/sessions/
│                      #      versions/assets/attachments
├── i18n/              # 保留框架（common/api/assets/settings 命名空间）
└── stores/            # 保留 chat/streaming 相关
```

---

## 四、工程规范

### 4.1 测试

- **分层**：unit（快，无外部依赖）/ integration（需 DB+Redis）/ e2e（需完整栈）
- **marker 体系**：沿用既有 pytest markers（unit/integration/slow/flaky/regression）
- **覆盖率门槛**：核心路径 ≥80%（RAG 管线、auth、keys 必须覆盖）
- **TDD**：新功能先写测试（红灯）→ 实现（绿灯）→ 重构
- 前端 vitest + Testing Library；关键交互组件必须有测试

### 4.2 CI/CD

- GitHub Actions 沿既有 CI 结构：changes 检测 → frontend-lint/typecheck → backend-lint/mypy → backend-test（pytest-split）→ build
- 门槛：ruff 0 error、mypy strict 0 error、tsc 0 error、pytest 全绿、覆盖率不下降
- 主分支 main/develop 保护 + PR 必须过 CI

### 4.3 Git 规范

- 分支：`feature/<名称>` / `fix/<名称>`，合入 develop 后再进 main
- 提交信息：`<type>: <简述>`（feat/fix/refactor/chore/docs），中英皆可但全库一致
- 提交粒度：一个逻辑变更一个提交，测试与实现同提交
- 禁止直接提交 main

### 4.4 文档规范

- README：架构图 + 快速开始 + 目录说明
- docs/SPEC.md（本文件）：规范总纲，变更必须同步更新
- API 变更必须同步更新本规范 3.3 节

### 4.5 裁剪边界

1. 允许保留：auth/keys/sessions/runs/streaming/prompts/versions/attachments/rag + 基础设施（core/broker/checkpoint/observability/upload）
2. 已删除：generation/compose/image/structured 服务与路由、compose_templates 表、content/history 前端层、generation 相关 i18n
3. 删除必须彻底：路由注册、import、测试引用同步清理，不得留死代码
4. 命名：`content`/`generation` 语义代码不得重新引入；知识库统一用 `assets` 语义

---

## 五、验收标准（Definition of Done）

- [ ] 后端启动无 import 错误，路由正常注册，health 检查通过
- [ ] 前端 tsc/eslint 零错误，登录 → 问答工作台可走通
- [ ] 知识库：文档上传 → 索引 → 列表/删除可用
- [ ] 问答：提问 → RAG 检索 → 流式回答全链路可用
- [ ] 单元/集成测试覆盖核心路径，CI 全绿
- [ ] README + 本规范文档与实际代码一致
