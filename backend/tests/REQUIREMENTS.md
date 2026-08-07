# 需求覆盖率追溯矩阵

本文档追踪需求与测试用例的映射关系，确保核心业务逻辑有测试覆盖。

## 使用方法

在测试用例中使用 `@pytest.mark.requirement("REQ-XXX")` 标记关联的需求：

```python
@pytest.mark.requirement("REQ-001")
async def test_login_success():
    """用户登录成功"""
    ...
```

CI 用 `pytest --requirement-coverage`（`tests/requirement_coverage.py` 插件）统计已标记的测试覆盖率。

**状态口径**：`✅` = 存在真实测试（带 file 证据，标 *marker* 的为 `@pytest.mark.requirement` 标记）；`📝` = 需求成立但缺测试。

---

## 认证模块 (Auth)

| 需求 ID | 需求描述 | 自动化测试用例 | 状态 |
|---------|---------|---------------|------|
| REQ-AUTH-001 | 用户名密码登录成功 | `tests/test_requirement_markers.py::test_login_success` *marker*；`tests/routers/auth/test_login.py` | ✅ |
| REQ-AUTH-002 | 密码错误提示 | `tests/test_requirement_markers.py::test_login_wrong_password` *marker* | ✅ |
| REQ-AUTH-003 | OAuth Google 登录 | —（后端无 OAuth provider 实现，ragbase 未启用） | 📝 |
| REQ-AUTH-004 | JWT Token 生成与验证 | `tests/auth/test_auth_jwt.py` *marker ×3* | ✅ |
| REQ-AUTH-005 | Token 刷新机制 | `tests/test_requirement_markers.py` *marker*；`tests/auth/test_auth_schemas.py::test_logout` 等 | ✅ |
| REQ-AUTH-006 | 登出与 Token 失效 | `tests/routers/auth/test_auth_api.py`、`tests/routers/auth/test_auth_routers.py` | ✅ |
| REQ-AUTH-007 | 密码强度策略 | `tests/auth/test_password_policy.py` *marker ×5* | ✅ |
| REQ-AUTH-008 | 账户锁定（5次错误） | `tests/auth/test_account_lockout.py` *marker ×3* | ✅ |
| REQ-AUTH-009 | RBAC 角色权限控制 | `tests/auth/test_auth_rbac.py` *marker ×6*；`tests/test_auth_roles.py` | ✅ |
| REQ-AUTH-010 | API Key 认证 | `tests/auth/test_auth_middleware.py` *marker ×2*；`tests/routers/commands/test_keys.py` | ✅ |

## 会话管理 (Sessions)

| 需求 ID | 需求描述 | 自动化测试用例 | 状态 |
|---------|---------|---------------|------|
| REQ-SES-001 | 创建新会话 | `tests/repository/test_sessions_runs_messages.py` *marker*；`tests/routers/test_routers_sessions.py` | ✅ |
| REQ-SES-002 | 获取会话列表 | `tests/repository/test_sessions_runs_messages.py` *marker* | ✅ |
| REQ-SES-003 | 获取会话详情 | `tests/repository/test_sessions_runs_messages.py` *marker* | ✅ |
| REQ-SES-004 | 删除会话 | `tests/repository/test_sessions_runs_messages.py::test_delete_session` *marker* | ✅ |
| REQ-SES-005 | 会话消息历史 | `tests/routers/test_routers_sessions.py`（消息列表随会话查询） | ✅ |
| REQ-SES-006 | 会话分页 | —（待实现：需要分页参数测试） | 📝 |
| REQ-SES-007 | 会话搜索 | —（待实现：需要关键词搜索接口测试） | 📝 |

## 运行管理 (Runs)

| 需求 ID | 需求描述 | 自动化测试用例 | 状态 |
|---------|---------|---------------|------|
| REQ-RUN-001 | 创建运行任务 | `tests/test_requirement_markers.py` *marker*；`tests/services/test_run_service.py` | ✅ |
| REQ-RUN-002 | 流式输出 | `tests/streaming/`（test_streaming / test_emitter_comprehensive / test_llm_stream / test_conversation）*marker ×21* | ✅ |
| REQ-RUN-003 | 运行状态查询 | `tests/tasks/test_agent_pipeline.py::test_run_status`；`tests/routers/test_routers_runs.py` | ✅ |
| REQ-RUN-004 | 运行取消 | `tests/tasks/test_agent_pipeline.py`、`tests/tasks/test_pipeline_utils.py` | ✅ |
| REQ-RUN-005 | 运行历史 | `tests/routers/test_routers_runs.py` | ✅ |
| REQ-RUN-006 | 继续生成（中断后恢复） | `tests/test_continue_generation.py` *marker*；`tests/routers/commands/test_run_continue.py` | ✅ |
| REQ-RUN-007 | 并发运行控制 | —（需要多实例基础设施，暂不阻塞） | 📝 |

## 模型管理 (Models)

| 需求 ID | 需求描述 | 自动化测试用例 | 状态 |
|---------|---------|---------------|------|
| REQ-MOD-001 | 模型列表 | `tests/routers/commands/test_models.py::test_list_models`；`tests/routers/test_keys_models.py` | ✅ |
| REQ-MOD-002 | 模型配置 | `tests/routers/commands/test_models.py`、`tests/routers/test_keys_models.py` | ✅ |
| REQ-MOD-003 | 模型提供商管理 | `tests/routers/commands/test_providers.py`、`tests/routers/test_provider_routes.py` | ✅ |

## Prompt 管理 (Prompts)

| 需求 ID | 需求描述 | 自动化测试用例 | 状态 |
|---------|---------|---------------|------|
| REQ-PROMPT-001 | 创建 Prompt | `tests/repository/test_prompts.py` *marker ×4*；`tests/routers/test_routers_prompts.py` | ✅ |
| REQ-PROMPT-002 | Prompt 版本管理 | `tests/repository/test_versions.py`、`tests/routers/test_routers_versions.py` | ✅ |
| REQ-PROMPT-003 | Prompt 模板变量 | `tests/repository/test_prompts.py`（模板渲染用例） | ✅ |

## 知识库 (RAG / Assets)

| 需求 ID | 需求描述 | 自动化测试用例 | 状态 |
|---------|---------|---------------|------|
| REQ-RAG-001 | 文档资产 CRUD 与用户级隔离 | `tests/repository/test_assets_repo.py::test_asset_crud_roundtrip`、`::test_get_asset_for_user_scoped` | ✅ |
| REQ-RAG-002 | 语义切块 | `tests/rag/test_rag_basic.py`（semantic_chunk 系列用例） | ✅ |
| REQ-RAG-003 | 向量化存储 | `tests/rag/test_rag_store.py`、`tests/rag/test_rag_embedding.py` | ✅ |
| REQ-RAG-004 | 相似性搜索 | `tests/rag/test_rag_store.py::test_search` | ✅ |
| REQ-RAG-005 | 检索增强生成管线 | `tests/rag/test_rag_pipeline.py`、`tests/rag/test_rag_init.py` | ✅ |
| REQ-RAG-006 | 上传/建索引 API（`POST /api/assets`、`POST /api/assets/{id}/index`） | —（routers/assets.py 缺专门路由测试，待补） | 📝 |

## 监控与可观测性 (Observability)

| 需求 ID | 需求描述 | 自动化测试用例 | 状态 |
|---------|---------|---------------|------|
| REQ-OBS-001 | 请求日志 | `tests/observability/test_observability.py` *marker*；`tests/core/test_request_logger.py` | ✅ |
| REQ-OBS-002 | 错误追踪 | `tests/observability/test_observability.py` *marker*；`tests/observability/test_analyzer.py` | ✅ |
| REQ-OBS-003 | 性能指标 | `tests/observability/test_router.py`、`tests/observability/test_store_queue.py` | ✅ |

---

## 底座保留模块（agent-studio 裁剪，非 ragbase 核心业务）

以下模块由 agent-studio 底座保留，e2e 回归测试存在但**不计入 ragbase 核心需求**：

| 模块 | e2e 回归测试 |
|---|---|
| agents（graph 单 agent 引擎的资源层） | `tests/e2e/test_agent_crud.py` |
| tools / mcp / skills | `tests/e2e/test_tool_crud.py`、`tests/e2e/test_mcp_crud.py`、`tests/e2e/test_mcp_invocation.py`、`tests/e2e/test_skill_crud.py` |
| workflows | `tests/e2e/test_workflow_crud.py` |
| teams | `tests/e2e/test_team_crud.py` |

---

## 统计摘要

| 模块 | 需求总数 | 已覆盖 | 覆盖率 |
|------|---------|--------|--------|
| 认证模块 | 10 | 9 | 90% |
| 会话管理 | 7 | 5 | 71% |
| 运行管理 | 7 | 6 | 86% |
| 模型管理 | 3 | 3 | 100% |
| Prompt 管理 | 3 | 3 | 100% |
| 知识库（RAG） | 6 | 5 | 83% |
| 监控 | 3 | 3 | 100% |
| **总计** | **39** | **34** | **87.2%** |

## 跟踪中的需求

1. **REQ-AUTH-003**: OAuth Google 登录 — ragbase 未启用 OAuth provider，实现后补测试
2. **REQ-SES-006**: 会话分页 — 需要补充分页参数的 API 测试
3. **REQ-SES-007**: 会话搜索 — 需要补充关键词搜索的 API 测试
4. **REQ-RUN-007**: 并发运行控制 — 需要多实例基础设施，暂不阻塞
5. **REQ-RAG-006**: assets 上传/索引 API 路由测试 — routers/assets.py 为 ragbase 核心，优先补充

> 注：历史矩阵（2026-08 前）曾引用不存在的函数名（如 `test_document_upload`/`test_rag_generation`）与已裁剪模块（agents/tools/workflows）需求，已全部按真实测试重写。
