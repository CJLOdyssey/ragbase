"""Seed realistic fake data for admin account — knowledge bases, assets, and prompts.

Usage:
    cd /path/to/ragbase && python3 backend/scripts/seed_fake_data.py

Idempotent: safe to run multiple times (skips existing items).
"""
import asyncio
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend", "src"))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/ragbase")

from core.infra.database import get_session_factory
from sqlalchemy import select

# ──────────────────────────────────────────────────────────────────────────────
# Knowledge Bases
# ──────────────────────────────────────────────────────────────────────────────
KNOWLEDGE_BASES = [
    {
        "name": "产品技术文档",
        "description": "产品架构设计、API 接口文档、技术规范、部署指南等技术类文档",
    },
    {
        "name": "业务运营资料",
        "description": "运营策略、市场分析、用户增长、数据分析报告等业务类文档",
    },
    {
        "name": "团队知识库",
        "description": "团队规范、开发流程、新人入职指南、会议纪要等团队协作文档",
    },
]

# ──────────────────────────────────────────────────────────────────────────────
# Assets — documents (md/txt/pdf)
# ──────────────────────────────────────────────────────────────────────────────
ASSETS = [
    # ── 产品技术文档 ──
    {
        "kb_name": "产品技术文档",
        "name": "系统架构设计 v2.0.md",
        "asset_type": "document",
        "format": "md",
        "content": """# 系统架构设计 v2.0

## 1. 架构概览

本系统采用微服务架构，核心模块包括：

- **网关层**：Nginx 反向代理 + 负载均衡
- **认证服务**：JWT + OAuth 2.0 双模式
- **业务服务**：FastAPI (Python 3.12)
- **数据层**：PostgreSQL 16 + Redis 7
- **向量引擎**：pgvector（RAG 检索）

## 2. 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| 后端框架 | FastAPI | 异步高性能，自动 API 文档 |
| ORM | SQLAlchemy 2.0 | 成熟稳定，async 支持 |
| 数据库 | PostgreSQL 16 | JSONB + pgvector 一站解决 |
| 缓存 | Redis 7 | 会话管理 + 消息队列 |
| 前端 | React + TypeScript | 类型安全，生态丰富 |

## 3. 部署架构

```
                    ┌─────────────┐
                    │   Nginx     │
                    │  (LB/TLS)   │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
     ┌──────▼──────┐ ┌─────▼──────┐ ┌────▼─────┐
     │  API Server │ │  API Server│ │ Celery   │
     │  (Port 8081)│ │  (Port 8082)│ │ Worker   │
     └──────┬──────┘ └─────┬──────┘ └────┬─────┘
            │              │              │
            └──────────────┼──────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌──▼─────┐ ┌───▼────┐
       │ PostgreSQL  │ │ Redis  │ │ pgvec  │
       │   (5433)    │ │ (6380) │ │        │
       └─────────────┘ └────────┘ └────────┘
```

## 4. 安全设计

- 所有 API 端点必须经过 AuthMiddleware
- API Key 使用 AES-256-GCM 加密存储
- 敏感操作记录审计日志
- CORS 严格限制来源域名
""",
    },
    {
        "kb_name": "产品技术文档",
        "name": "API 接口规范.md",
        "asset_type": "document",
        "format": "md",
        "content": """# API 接口规范

## RESTful 设计原则

### HTTP 方法语义

| 方法 | 用途 | 幂等 | 安全 |
|------|------|------|------|
| GET | 查询资源 | ✓ | ✓ |
| POST | 创建资源 | ✗ | ✗ |
| PUT | 全量更新 | ✓ | ✗ |
| PATCH | 部分更新 | ✓ | ✗ |
| DELETE | 删除资源 | ✓ | ✗ |

### 状态码规范

- `200` OK — 成功
- `201` Created — 创建成功
- `400` Bad Request — 参数错误
- `401` Unauthorized — 未认证
- `403` Forbidden — 无权限
- `404` Not Found — 资源不存在
- `422` Unprocessable Entity — 业务校验失败
- `500` Internal Server Error — 服务端异常

### 响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "uuid",
    "created_at": "2026-01-01T00:00:00Z"
  }
}
```

### 分页规范

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "has_more": true
}
```

## 认证方式

1. **JWT Token**：放在 `Authorization: Bearer <token>` 头
2. **API Key**：放在 `X-API-Key` 头（仅限服务端调用）
""",
    },
    {
        "kb_name": "产品技术文档",
        "name": "数据库设计文档.md",
        "asset_type": "document",
        "format": "md",
        "content": """# 数据库设计文档

## 核心表结构

### users — 用户表

```sql
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    auth_provider VARCHAR(16) DEFAULT 'email',
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### sessions — 会话表

```sql
CREATE TABLE sessions (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(256) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    kind VARCHAR(16) DEFAULT 'normal',
    is_pinned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### assets — 素材表

```sql
CREATE TABLE assets (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    name VARCHAR(256) NOT NULL,
    asset_type VARCHAR(32) DEFAULT 'document',
    format VARCHAR(16),
    size_bytes INTEGER DEFAULT 0,
    storage_path VARCHAR(512) NOT NULL,
    source VARCHAR(16) DEFAULT 'upload',
    knowledge_base_id VARCHAR(36),
    usage_count INTEGER DEFAULT 0,
    indexed BOOLEAN DEFAULT FALSE,
    tags JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## 索引策略

- `users.email` — 唯一索引（登录查询）
- `sessions.user_id` — 普通索引（用户会话列表）
- `assets.user_id + knowledge_base_id` — 复合索引（素材筛选）
- `vector_chunks.asset_id` — 普通索引（RAG 检索）
""",
    },
    {
        "kb_name": "产品技术文档",
        "name": "部署运维手册.md",
        "asset_type": "document",
        "format": "md",
        "content": """# 部署运维手册

## 环境要求

- Docker 24+ / Docker Compose v2
- Python 3.12+
- Node.js 20+
- PostgreSQL 16 + pgvector 扩展

## 本地开发

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/ragbase.git
cd ragbase

# 2. 启动数据库
docker compose -f docker/compose.base.yml up -d postgres redis

# 3. 启动后端
cd backend && pip install -e ".[dev]"
make dev-backend

# 4. 启动前端
cd frontend && npm install && npm run dev
```

## 生产部署

### Docker Compose 部署

```bash
# 构建并启动所有服务
docker compose -f docker/compose.base.yml -f docker/compose.prod.yml up -d

# 查看日志
docker compose logs -f backend

# 数据库迁移
docker compose exec backend python -m alembic upgrade head
```

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| DATABASE_URL | 数据库连接 | postgresql+asyncpg://... |
| REDIS_URL | Redis 连接 | redis://localhost:6380 |
| JWT_SECRET | JWT 密钥 | (必须设置) |
| ENCRYPTION_KEY | API Key 加密密钥 | (必须设置) |

## 监控告警

- 健康检查：`GET /api/health`
- 就绪检查：`GET /api/ready`
- Prometheus 指标：`GET /metrics`
""",
    },
    # ── 业务运营资料 ──
    {
        "kb_name": "业务运营资料",
        "name": "Q3 运营策略.md",
        "asset_type": "document",
        "format": "md",
        "content": """# Q3 运营策略

## 核心目标

| 指标 | 目标值 | 当前值 | 增幅 |
|------|--------|--------|------|
| MAU | 5,000+ | 3,200 | +56% |
| 留存率 | >40% | 32% | +8pp |
| NPS 评分 | >30 | 24 | +6 |
| 付费转化率 | >5% | 3.2% | +1.8pp |

## 关键举措

### 1. 内容营销（7月）

- 每周发布 2 篇技术博客（RAG、AI 应用）
- 制作 3 个产品演示视频
- 参与 2 场技术社区分享

### 2. 用户增长（8月）

- 推出邀请奖励计划（邀请 1 人得 1 个月 Pro）
- 与 3 个开发者社区合作推广
- 举办首场线上 Workshop

### 3. 产品迭代（9月）

- 上线团队协作功能
- 优化移动端体验
- 发布 v2.0 版本

## 预算分配

| 项目 | 预算 | 占比 |
|------|------|------|
| 内容制作 | ¥15,000 | 30% |
| 社区推广 | ¥20,000 | 40% |
| 活动运营 | ¥10,000 | 20% |
| 工具订阅 | ¥5,000 | 10% |
| **合计** | **¥50,000** | 100% |
""",
    },
    {
        "kb_name": "业务运营资料",
        "name": "竞品分析报告.md",
        "asset_type": "document",
        "format": "md",
        "content": """# 竞品分析报告

## 竞品概览

| 产品 | 定位 | 月活 | 核心优势 | 主要短板 |
|------|------|------|----------|----------|
| 竞品 A | 企业知识库 | 50K+ | 品牌知名度高 | 价格贵，定制性差 |
| 竞品 B | AI 助手 | 30K+ | 功能全面 | 学习曲线陡峭 |
| 竞品 C | 开源方案 | 10K+ | 免费、可定制 | 需自运维 |
| **我们** | RAG 知识库 | 3K+ | 专注 RAG、易用 | 品牌弱 |

## 功能对比矩阵

| 功能 | 竞品A | 竞品B | 竞品C | 我们 |
|------|-------|-------|-------|------|
| 文档上传 | ✓ | ✓ | ✓ | ✓ |
| RAG 检索 | △ | ✓ | ✓ | ✓ |
| 多知识库 | ✓ | ✓ | △ | ✓ |
| 团队协作 | ✓ | ✓ | ✗ | △ |
| API 集成 | ✓ | ✓ | ✓ | ✓ |
| 本地部署 | △ | ✗ | ✓ | ✓ |
| 中文优化 | △ | ✓ | ✗ | ✓ |

## 差异化策略

1. **专注 RAG**：深耕检索增强生成，召回率业界领先
2. **中文友好**：针对中文分词、语义优化
3. **灵活部署**：支持 SaaS / 私有化 / 混合云
4. **性价比**：同等功能 50% 价格
""",
    },
    {
        "kb_name": "业务运营资料",
        "name": "用户反馈汇总.md",
        "asset_type": "document",
        "format": "md",
        "content": """# 用户反馈汇总（2026年8月）

## 反馈统计

- 总反馈数：156 条
- 已处理：128 条（82%）
- 待处理：28 条（18%）

## 高频需求 TOP 5

| 排名 | 需求 | 提及次数 | 优先级 |
|------|------|----------|--------|
| 1 | 支持更多文件格式（Excel、PPT） | 42 | P0 |
| 2 | 团队协作空间 | 38 | P1 |
| 3 | 移动端适配 | 29 | P1 |
| 4 | API 限流配置 | 21 | P2 |
| 5 | 自定义品牌 Logo | 18 | P2 |

## 典型反馈

### 正面反馈
> "RAG 检索效果比竞品好很多，召回率很高" — 某科技公司 CTO
> "界面简洁，上手很快" — 某创业公司 PM

### 改进建议
> "希望支持 Excel 和 PPT 上传" — 某金融公司分析师
> "需要团队空间功能，方便多人协作" — 某互联网公司开发

## 处理计划

1. **本周**：上线 Excel/CSV 支持
2. **下周**：启动团队空间设计
3. **月底**：移动端适配 v1
""",
    },
    # ── 团队知识库 ──
    {
        "kb_name": "团队知识库",
        "name": "新人入职指南.md",
        "asset_type": "document",
        "format": "md",
        "content": """# 新人入职指南

## 欢迎加入！

恭喜你成为团队的一员！这份指南将帮助你快速融入。

## 第一天

- [ ] 领取设备（MacBook Pro M3）
- [ ] 开通企业邮箱和 Slack
- [ ] 加入 GitHub 组织
- [ ] 与导师见面

## 第一周

- [ ] 阅读产品文档（见知识库）
- [ ] 搭建本地开发环境
- [ ] 完成第一个 Hello World PR
- [ ] 参加团队周会

## 常用资源

| 资源 | 地址 | 说明 |
|------|------|------|
| GitHub | github.com/your-org | 代码仓库 |
| Notion | notion.so/your-org | 文档中心 |
| Slack | your-org.slack.com | 即时通讯 |
| Figma | figma.com/your-org | 设计稿 |

## 开发规范

1. **分支命名**：`feat/xxx`、`fix/xxx`、`docs/xxx`
2. **提交信息**：Conventional Commits 格式
3. **代码审查**：至少 1 人 Approve
4. **测试覆盖**：新功能必须有测试

## 联系方式

- **HR**：hr@company.com（考勤、假期）
- **IT**：it@company.com（设备、权限）
- **导师**：入职时分配
""",
    },
    {
        "kb_name": "团队知识库",
        "name": "代码审查规范.md",
        "asset_type": "document",
        "format": "md",
        "content": """# 代码审查规范

## 审查原则

1. **建设性**：提出改进建议，而非批评
2. **具体性**：指出具体行号和问题
3. **及时性**：24 小时内完成审查
4. **学习性**：分享知识，共同成长

## 审查清单

### 代码质量
- [ ] 代码逻辑清晰，易于理解
- [ ] 没有重复代码（DRY 原则）
- [ ] 函数长度合理（<50 行）
- [ ] 变量命名有意义

### 安全性
- [ ] 无硬编码敏感信息
- [ ] 输入已做校验
- [ ] SQL 查询使用参数化
- [ ] 权限检查完整

### 测试
- [ ] 新增功能有单元测试
- [ ] 边界情况已覆盖
- [ ] 测试可重复运行

### 性能
- [ ] 无 N+1 查询
- [ ] 大数据集使用分页
- [ ] 缓存使用合理

## 评论格式

```
[严重程度] 问题描述
建议：改进方案
参考：相关文档/示例
```

严重程度：`blocking`（必须改）、`suggestion`（建议改）、`nit`（小问题）
""",
    },
]

# ──────────────────────────────────────────────────────────────────────────────
# Prompts
# ──────────────────────────────────────────────────────────────────────────────
PROMPTS = [
    # ── 系统提示词 ──
    {
        "name": "RAG 检索增强问答",
        "description": "基于检索到的上下文回答用户问题，防止幻觉",
        "category": "system",
        "content": """你是一个企业知识库问答助手。请严格基于以下检索到的上下文回答问题。

规则：
1. 如果上下文中没有相关信息，请明确告知"根据现有知识库，我无法找到相关信息"
2. 不要编造或推测不在上下文中的信息
3. 引用来源时标注 [来源X]
4. 回答要简洁准确，避免冗余
5. 如果问题模糊，先澄清再回答

检索到的上下文：
{context}

用户问题：{query}""",
        "model": None,
    },
    {
        "name": "代码审查助手",
        "description": "对代码进行安全、性能、可维护性审查",
        "category": "system",
        "content": """你是一位资深代码审查专家。请对以下代码进行审查，关注：

1. **安全漏洞**：SQL 注入、XSS、CSRF、硬编码密钥等
2. **性能问题**：N+1 查询、内存泄漏、不必要的循环等
3. **代码规范**：命名、结构、注释、复杂度
4. **边界情况**：空值处理、异常捕获、并发问题

请按严重程度排列问题，并给出具体的修改建议。

代码：
```{language}
{code}
```""",
        "model": "anthropic/claude-sonnet-4-5",
    },
    {
        "name": "技术文档生成器",
        "description": "根据代码或需求自动生成技术文档",
        "category": "system",
        "content": """你是一位技术文档专家。请根据以下信息生成专业的技术文档。

要求：
1. 结构清晰，使用 Markdown 格式
2. 包含背景、设计、实现、使用说明
3. 代码示例完整可运行
4. 考虑边界情况和常见问题

输入信息：
{input}""",
        "model": None,
    },
    # ── 用户提示词 ──
    {
        "name": "SQL 查询优化器",
        "description": "分析 SQL 查询并提供优化建议",
        "category": "user",
        "content": """请分析以下 SQL 查询并提供优化建议：

1. 执行计划分析
2. 索引建议
3. 查询重写方案
4. 潜在的性能瓶颈

数据库类型：{db_type}
表结构：
{schema}

查询语句：
```sql
{query}
```""",
        "model": "anthropic/claude-sonnet-4-5",
    },
    {
        "name": "API 文档生成",
        "description": "根据代码自动生成 API 文档",
        "category": "user",
        "content": """请根据以下代码片段生成完整的 API 文档：

1. 接口名称和描述
2. 请求方法和路径
3. 请求参数（路径参数、查询参数、请求体）
4. 响应格式和状态码
5. 使用示例（cURL / Python）

代码：
```{language}
{code}
```""",
        "model": None,
    },
    {
        "name": "测试用例生成",
        "description": "为函数/类生成单元测试",
        "category": "user",
        "content": """请为以下代码生成完整的单元测试：

1. 覆盖正常路径和边界情况
2. 包含异常处理测试
3. 使用 mock 模拟外部依赖
4. 测试命名清晰明了

代码：
```{language}
{code}
```

测试框架：{framework}""",
        "model": "anthropic/claude-haiku-4-5",
    },
    # ── 元提示词 ──
    {
        "name": "提示词优化器",
        "description": "优化提示词以获得更好的 AI 输出",
        "category": "meta",
        "content": """请优化以下提示词，使其更清晰、更具体、更有效：

1. 明确角色和职责
2. 细化输出格式要求
3. 添加约束条件
4. 包含示例（如适用）

原始提示词：
{prompt}

请输出优化后的提示词，并解释改进点。""",
        "model": "anthropic/claude-haiku-4-5",
    },
    {
        "name": "多语言翻译专家",
        "description": "高质量中英文互译，保持专业术语准确",
        "category": "meta",
        "content": """你是专业翻译，请将以下内容翻译为 {target_lang}。

要求：
1. 保持原文语气和风格
2. 专业术语准确（参考行业标准）
3. 符合目标语言的表达习惯
4. 保持格式一致（标题、列表、代码块等）
5. 如有不确定的术语，给出译文并标注原文

原文：
{text}""",
        "model": None,
    },
]


async def main():
    factory = get_session_factory()

    # Get admin user ID
    async with factory() as session:
        from orm.auth import UserDB
        r = await session.execute(select(UserDB).where(UserDB.username == "admin"))
        admin = r.scalar_one_or_none()
        if not admin:
            print("❌ Admin user not found. Run the app first to seed it.")
            return
        admin_id = admin.id
        print(f"✅ Found admin user: {admin.username} ({admin_id})")

    # ── Seed knowledge bases ──
    kb_id_map = {}
    async with factory() as session:
        from orm.infra import KnowledgeBaseDB
        r = await session.execute(select(KnowledgeBaseDB))
        existing = {kb.name: kb.id for kb in r.scalars().all()}
        count = 0
        for kb in KNOWLEDGE_BASES:
            if kb["name"] in existing:
                kb_id_map[kb["name"]] = existing[kb["name"]]
                continue
            new_kb = KnowledgeBaseDB(
                user_id=admin_id, name=kb["name"], description=kb["description"]
            )
            session.add(new_kb)
            await session.flush()
            kb_id_map[kb["name"]] = new_kb.id
            count += 1
        await session.commit()
        print(f"✅ Knowledge Bases: {count} created, {len(KNOWLEDGE_BASES) - count} skipped")

    # ── Seed assets ──
    uploads_dir = os.path.join(PROJECT_ROOT, "backend", "uploads", "seed")
    os.makedirs(uploads_dir, exist_ok=True)

    async with factory() as session:
        from orm.infra import AssetDB
        r = await session.execute(select(AssetDB))
        existing = {a.name for a in r.scalars().all()}
        count = 0
        for a in ASSETS:
            if a["name"] in existing:
                continue
            # Write placeholder file
            safe_name = a["name"].replace("/", "_")
            file_path = os.path.join(uploads_dir, safe_name)
            with open(file_path, "w") as f:
                f.write(a["content"])

            kb_id = kb_id_map.get(a["kb_name"])
            session.add(
                AssetDB(
                    user_id=admin_id,
                    name=a["name"],
                    asset_type=a["asset_type"],
                    format=a.get("format"),
                    size_bytes=len(a["content"].encode()),
                    storage_path=file_path,
                    source="upload",
                    knowledge_base_id=kb_id,
                    indexed=False,
                )
            )
            count += 1
        await session.commit()
        print(f"✅ Assets: {count} created, {len(ASSETS) - count} skipped")

    # ── Seed prompts ──
    async with factory() as session:
        from orm.prompt_db import PromptDB
        r = await session.execute(select(PromptDB))
        existing = {p.name for p in r.scalars().all()}
        count = 0
        for p in PROMPTS:
            if p["name"] in existing:
                continue
            session.add(
                PromptDB(
                    name=p["name"],
                    description=p["description"],
                    category=p["category"],
                    content=p["content"],
                    model=p["model"],
                    status="enabled",
                    version="v1.0.0",
                    owner_id=admin_id,
                )
            )
            count += 1
        await session.commit()
        print(f"✅ Prompts: {count} created, {len(PROMPTS) - count} skipped (existing)")

    print("\n🎉 Seed complete! Refresh the admin pages to see data.")


if __name__ == "__main__":
    asyncio.run(main())
