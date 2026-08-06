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

CI 脚本会统计已标记的测试覆盖率。

---

## 认证模块 (Auth)

| 需求 ID | 需求描述 | 自动化测试用例 | 状态 |
|---------|---------|---------------|------|
| REQ-AUTH-001 | 用户名密码登录成功 | `test_login_success` | ✅ |
| REQ-AUTH-002 | 密码错误提示 | `test_login_wrong_password` | ✅ |
| REQ-AUTH-003 | OAuth Google 登录 | `test_login_google_success` | ✅ |
| REQ-AUTH-004 | JWT Token 生成与验证 | `test_jwt_token_generation`, `test_jwt_token_validation` | ✅ |
| REQ-AUTH-005 | Token 刷新机制 | `test_token_refresh` | ✅ |
| REQ-AUTH-006 | 登出与 Token 失效 | `test_logout_token_invalidation` | ✅ |
| REQ-AUTH-007 | 密码强度策略 | `test_password_policy_strong`, `test_password_policy_weak` | ✅ |
| REQ-AUTH-008 | 账户锁定（5次错误） | `test_increment_failed_logins`, `test_lockout_after_5_failures`, `test_lockout_duration_is_15_minutes`, `test_successful_login_resets_failed_attempts`, `test_reset_failed_logins_unlocks_account` | ✅ |
| REQ-AUTH-009 | RBAC 角色权限控制 | `test_rbac_admin_access`, `test_rbac_user_access` | ✅ |
| REQ-AUTH-010 | API Key 认证 | `test_api_key_auth` | ✅ |

## 会话管理 (Sessions)

| 需求 ID | 需求描述 | 自动化测试用例 | 状态 |
|---------|---------|---------------|------|
| REQ-SES-001 | 创建新会话 | `test_create_session` | ✅ |
| REQ-SES-002 | 获取会话列表 | `test_list_sessions` | ✅ |
| REQ-SES-003 | 获取会话详情 | `test_get_session` | ✅ |
| REQ-SES-004 | 删除会话 | `test_delete_session` | ✅ |
| REQ-SES-005 | 会话消息历史 | `test_session_messages` | ✅ |
| REQ-SES-006 | 会话分页 | —（待实现：需要分页参数测试） | 📝 |
| REQ-SES-007 | 会话搜索 | —（待实现：需要关键词搜索接口测试） | 📝 |

## Agent 配置 (Agents)

| 需求 ID | 需求描述 | 自动化测试用例 | 状态 |
|---------|---------|---------------|------|
| REQ-AGT-001 | 创建 Agent | `test_create_agent` | ✅ |
| REQ-AGT-002 | 更新 Agent 配置 | `test_update_agent` | ✅ |
| REQ-AGT-003 | 删除 Agent | `test_delete_agent` | ✅ |
| REQ-AGT-004 | Agent 工具绑定 | `test_agent_tool_binding` | ✅ |
| REQ-AGT-005 | Agent Prompt 绑定 | `test_agent_prompt_binding` | ✅ |
| REQ-AGT-006 | Agent 模型选择 | `test_agent_model_selection` | ✅ |

## 运行管理 (Runs)

| 需求 ID | 需求描述 | 自动化测试用例 | 状态 |
|---------|---------|---------------|------|
| REQ-RUN-001 | 创建运行任务 | `test_create_run` | ✅ |
| REQ-RUN-002 | 流式输出 | `test_streaming_output` | ✅ |
| REQ-RUN-003 | 运行状态查询 | `test_run_status` | ✅ |
| REQ-RUN-004 | 运行取消 | `test_cancel_run` | ✅ |
| REQ-RUN-005 | 运行历史 | `test_run_history` | ✅ |
| REQ-RUN-006 | 继续生成（中断后恢复） | `test_continue_run_creates_new_session_when_none`, `test_continue_run_uses_existing_session`, `test_continue_run_requires_api_key`, `test_complete_run_endpoint_success` | ✅ |
| REQ-RUN-007 | 并发运行控制 | —（需要多实例基础设施，暂不阻塞） | 📝 |

## 工具管理 (Tools)

| 需求 ID | 需求描述 | 自动化测试用例 | 状态 |
|---------|---------|---------------|------|
| REQ-TOOL-001 | 创建自定义工具 | `test_create_tool` | ✅ |
| REQ-TOOL-002 | 工具参数验证 | `test_tool_parameter_validation` | ✅ |
| REQ-TOOL-003 | 工具执行 | `test_tool_execution` | ✅ |
| REQ-TOOL-004 | MCP 工具集成 | `test_mcp_tool_integration` | ✅ |
| REQ-TOOL-005 | Skill 工具集成 | `test_skill_tool_integration` | ✅ |

## 工作流 (Workflows)

| 需求 ID | 需求描述 | 自动化测试用例 | 状态 |
|---------|---------|---------------|------|
| REQ-WF-001 | 创建工作流 | `test_create_workflow` | ✅ |
| REQ-WF-002 | DAG 配置 | `test_dag_configuration` | ✅ |
| REQ-WF-003 | 工作流执行 | `test_workflow_execution` | ✅ |
| REQ-WF-004 | 工作流可视化 | —（前端可视化功能，不通过 pytest 测试） | 📝 |

## 模型管理 (Models)

| 需求 ID | 需求描述 | 自动化测试用例 | 状态 |
|---------|---------|---------------|------|
| REQ-MOD-001 | 模型列表 | `test_list_models` | ✅ |
| REQ-MOD-002 | 模型配置 | `test_model_config` | ✅ |
| REQ-MOD-003 | 模型提供商管理 | `test_provider_management` | ✅ |

## Prompt 管理 (Prompts)

| 需求 ID | 需求描述 | 自动化测试用例 | 状态 |
|---------|---------|---------------|------|
| REQ-PROMPT-001 | 创建 Prompt | `test_create_prompt` | ✅ |
| REQ-PROMPT-002 | Prompt 版本管理 | `test_prompt_versioning` | ✅ |
| REQ-PROMPT-003 | Prompt 模板变量 | `test_prompt_variables` | ✅ |

## 知识库 (RAG)

| 需求 ID | 需求描述 | 自动化测试用例 | 状态 |
|---------|---------|---------------|------|
| REQ-RAG-001 | 文档上传 | `test_document_upload` | ✅ |
| REQ-RAG-002 | 向量化存储 | `test_vector_storage` | ✅ |
| REQ-RAG-003 | 相似性搜索 | `test_similarity_search` | ✅ |
| REQ-RAG-004 | 检索增强生成 | `test_rag_generation` | ✅ |

## 监控与可观测性 (Observability)

| 需求 ID | 需求描述 | 自动化测试用例 | 状态 |
|---------|---------|---------------|------|
| REQ-OBS-001 | 请求日志 | `test_request_logging` | ✅ |
| REQ-OBS-002 | 错误追踪 | `test_error_tracking` | ✅ |
| REQ-OBS-003 | 性能指标 | `test_metrics_collection` | ✅ |

---

## 统计摘要

| 模块 | 需求总数 | 已覆盖 | 覆盖率 |
|------|---------|--------|--------|
| 认证模块 | 10 | 10 | 100% |
| 会话管理 | 7 | 5 | 71% |
| Agent 配置 | 6 | 6 | 100% |
| 运行管理 | 7 | 6 | 86% |
| 工具管理 | 5 | 5 | 100% |
| 工作流 | 4 | 3 | 75% |
| 模型管理 | 3 | 3 | 100% |
| Prompt 管理 | 3 | 3 | 100% |
| 知识库 | 4 | 4 | 100% |
| 监控 | 3 | 3 | 100% |
| **总计** | **52** | **48** | **92.3%** |

## 跟踪中的需求

以下需求已有对应测试覆盖方向但暂未标记为正式通过：

1. **REQ-SES-006**: 会话分页 — 需要补充分页参数的 API 测试
2. **REQ-SES-007**: 会话搜索 — 需要补充关键词搜索的 API 测试
3. **REQ-RUN-007**: 并发运行控制 — 需要多实例基础设施，暂不阻塞
4. **REQ-WF-004**: 工作流可视化 — 前端 DAG 渲染功能，通过前端测试覆盖
