# RagBase 项目现状（2026-08-07）

## 一、项目定位

RAG 知识库问答平台：上传私有文档构建知识库，检索增强生成（RAG）提供带来源引用的问答。
独立项目、独立仓库。技术底座（auth/keys/sessions/runs/streaming/prompts/versions/rag）为自研裁剪体系。
规范驱动开发，规范见 `docs/SPEC.md`。

## 二、运行状态（当前）

| 服务 | 端口 | 状态 |
|---|---|---|
| 后端 | 8081 | health 200，连 `ragbase` 库（5433） |
| 前端 | 5174 | 200，proxy → 8081 |
| postgres | 5433 | `ragbase-db` 独立容器（pgvector/pg16，`ragbase` 库） |
| redis | 6380 | `ragbase-redis` 独立容器 |

标准启动命令（混合模式，开发推荐）：

```bash
docker compose -f docker/compose.base.yml -f docker/compose.local.yml up -d postgres redis
systemctl --user restart ragbase-backend   # 后端：systemd user service 守护（已 enable 开机自启）
cd frontend && npm run dev
# 服务文件：~/.config/systemd/user/ragbase-backend.service
# 重启/状态/日志：systemctl --user restart|status ragbase-backend ; journalctl --user -u ragbase-backend -f
```

> 备用（无 systemd 环境）：`make dev-backend`（脚本 `scripts/dev/run-backend.sh`，单实例 + 端口杀 + setsid 脱离，日志 `/tmp/ragbase-backend.log`）。`run-backend.sh` 与 systemd 服务文件均已强制正确 `DATABASE_URL`（自动重置被 opencode 沙箱泄漏的 `file:...sqlite` 污染值）。

## 三、数据库与依赖环境

- ragbase → `ragbase` 库（**独立容器** `ragbase-db`：5433，pgvector/pg16；alembic head = `p9g3n014`）
- ragbase → `ragbase-redis`（**独立容器**：6380）

## 四、验证门

```bash
make lint-backend        # ruff
make typecheck-backend   # mypy strict
make test-backend-quick  # pytest
cd frontend && npx tsc --noEmit && npx eslint src/ && npx vitest run
```

## 五、配置文档

- `AGENTS.md`（项目根）：第一性原理审视规则 + 启动/环境/验证门
- `docs/SPEC.md`：项目规范（约束/功能/技术/工程/验收）
- 全局 `~/.config/opencode/AGENTS.md`：caveman/ponytail 等 skill 清单
