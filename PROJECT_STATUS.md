# ContentStudio 项目现状（2026-08-06）

## 一、项目定位

内容创作助手（小红书笔记 / 公众号文章 / 短视频脚本 / 营销文案 + AI 配图合成卡片）。
独立项目、独立仓库。技术底座（auth/keys/sessions/runs/streaming/prompts/versions/rag）从 agent-studio 裁剪而来。
规范驱动开发，规范见 `docs/SPEC.md`。

## 二、git 历史

```
a1d68f4 docs: align README startup with content_studio db; fix script names
d336e4d chore: isolate content-studio env from agent-studio
9c1e9cd refactor: strip agent-studio leftovers per SPEC 4.5
579e625 feat: init ContentStudio from agent-studio skeleton
```

- `9c1e9cd`：按 SPEC 4.5 裁剪 agent-studio 残留（删 105 文件：system_team/thinking_tree/AgentStudio 组件/工具链等，orm 删 9 表模型）
- `d336e4d`：环境隔离（compose 改名 content-studio-*，alembic.ini 库指向 content_studio）
- `a1d68f4`：README/脚本对齐（DATABASE_URL 指向、PIDFILE、e2e 容器名）

## 三、运行状态（当前）

| 服务 | 端口 | 状态 |
|---|---|---|
| 后端 | 8081 | ✅ health 200，连 `content_studio` 库 |
| 前端 | 5174 | ✅ 200，proxy → 8081 |
| postgres/redis | docker 容器 | ✅ 运行中 |

标准启动命令（混合模式，开发推荐）：

```bash
docker compose -f docker/compose.base.yml -f docker/compose.local.yml up -d postgres redis
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/content_studio" make dev-backend
cd frontend && npm run dev
```

> 注意：DATABASE_URL 必须显式注入（run-backend.sh 不读 .env 兜底；opencode 沙箱会泄漏 `DATABASE_URL=file:...` 覆盖 .env）。

## 四、数据库隔离

- content-studio → `content_studio` 库（独立，17 张表，alembic_version = `c0nt3nt01drop`）
- agent-studio → `backend` 库（表结构已恢复，数据无损失，**不再触碰**）
- 已授权范围：不得修改 agent-studio 的代码/数据/进程/配置

## 五、裁剪边界（已完成）

已删：多 Agent 编排（teams/agents/agent_configs）、工具生态（tools/mcps/skills）、工作流（workflow）、system_team/thinking_tree、AgentStudio 前端组件、CLI main.py。
保留：auth/sessions/runs/prompts/versions/rag/attachments、SingleAgentGraph（单 agent 引擎）、生成管线基础。

## 六、待办：P9 SPEC 新功能（已完成）

| 项 | 内容 | 状态 |
|---|---|---|
| 调研 | run_service / attachments / providers 复用点 | ✅ 已调研（多源参照见实施计划） |
| alembic | project_runs 加列 + assets + compose_templates 表 + seed | ✅ 已实现（p9g3n001） |
| generation_service | 生成编排（校验/提示词/结构化/存版本） | ✅ 已实现 |
| image_service | 文生图 provider（OpenAI/DashScope 通义万相/Stability） | ✅ 已实现 |
| routers/generation | POST /api/generations + continue/variations/image/compose | ✅ 已实现 |
| assets | 素材库 CRUD + RAG index | ✅ 已实现 |
| compose_templates | 内置 3 套卡片模板 + GET /api/compose-templates | ✅ 已实现（seed） |
| 测试+验证门 | ruff/mypy/pytest/tsc/vitest/eslint | ✅ 全绿（见下） |

验证门结果：ruff 0 error / mypy strict 0 error / pytest 1346 过 7 跳过（含 P9 新增 39 用例）/ tsc 0 error / eslint 0 error / vitest 445/445；generation 管线覆盖率 81%（generation_service 81%、image_service 82%、structured 100%，SPEC §4.1 ≥80%）。

实施计划：`docs/superpowers/plans/2026-08-06-p9-generation-pipeline.md`

当前生成链路：类型化生成（content_type/主题校验 → vault key → run 创建 → LLM SSE → 结构化解析 → 版本+草稿），配素材 RAG + compose 模板 + 文生图。冒烟已验证：GET /api/compose-templates 3 套模板、POST /api/generations 返回 run_id（无真实 key 时管线入 error 态）。

## 七、配置文档

- `AGENTS.md`（项目根，gitignore 不入库）：第一性原理审视规则 + 启动/环境/验证门
- `docs/SPEC.md`：项目规范（约束/功能/技术/工程/验收）
- 全局 `~/.config/opencode/AGENTS.md`：caveman/ponytail 等 skill 清单

## 八、验证门

```bash
make lint-backend        # ruff
make typecheck-backend   # mypy strict
make test-backend-quick  # pytest
cd frontend && npx tsc --noEmit && npx eslint src/ && npx vitest run
```

上次全量（P9 收尾）：ruff 0 错、mypy strict 0 错、pytest 1346 过 7 跳过、tsc 0 错、vitest 445/445、eslint 0 错。
