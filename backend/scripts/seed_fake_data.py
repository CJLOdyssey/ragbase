"""Seed fake data for admin account — prompts + assets/knowledge bases."""
import asyncio
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend", "src"))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/ragbase")

from core.infra.database import get_session_factory
from sqlalchemy import select

PROMPTS = [
    {"name": "代码审查助手", "description": "对代码进行安全、性能、可维护性审查", "category": "system",
     "content": "你是一位资深代码审查专家。请对以下代码进行审查，关注：\n1. 安全漏洞（SQL注入、XSS、CSRF等）\n2. 性能问题（N+1查询、内存泄漏等）\n3. 代码规范（命名、结构、注释）\n4. 潜在的边界情况\n\n请按严重程度排列问题，并给出具体的修改建议。",
     "model": "anthropic/claude-sonnet-4-5"},
    {"name": "RAG 检索增强提示", "description": "基于检索到的上下文回答用户问题（OWASP LLM01 防护）", "category": "system",
     "content": "你是一个企业知识库问答助手。请严格基于以下检索到的上下文回答问题。\n\n规则：\n1. 如果上下文中没有相关信息，请明确告知用户你无法回答\n2. 不要编造或推测不在上下文中的信息\n3. 引用来源时标注 [来源X]\n4. 回答要简洁准确，避免冗余\n\n检索到的上下文：\n{context}\n\n用户问题：{query}",
     "model": None},
    {"name": "数据库查询优化器", "description": "分析 SQL 查询并提供优化建议", "category": "system",
     "content": "你是数据库优化专家。请分析以下 SQL 查询并提供优化建议：\n1. 执行计划分析\n2. 索引建议\n3. 查询重写方案\n4. 潜在的性能瓶颈\n\n数据库类型：{db_type}\n查询语句：\n{query}",
     "model": "anthropic/claude-sonnet-4-5"},
    {"name": "API 文档生成器", "description": "根据代码自动生成 API 文档", "category": "user",
     "content": "请根据以下代码片段生成完整的 API 文档，包括：\n1. 接口名称和描述\n2. 请求方法和路径\n3. 请求参数（路径参数、查询参数、请求体）\n4. 响应格式和状态码\n5. 使用示例\n\n代码：\n{code}",
     "model": None},
    {"name": "单元测试生成器", "description": "为函数/类生成单元测试", "category": "user",
     "content": "请为以下代码生成完整的单元测试：\n1. 覆盖正常路径和边界情况\n2. 包含异常处理测试\n3. 使用 mock 模拟外部依赖\n4. 测试命名清晰明了\n\n代码：\n{code}\n测试框架：{framework}",
     "model": "anthropic/claude-haiku-4-5"},
    {"name": "技术方案评审", "description": "评审技术方案的可行性和风险", "category": "user",
     "content": "请评审以下技术方案，从以下维度分析：\n1. 技术可行性（1-10分）\n2. 实现复杂度（1-10分）\n3. 潜在风险和缓解措施\n4. 替代方案对比\n5. 建议的实施步骤\n\n技术方案：\n{proposal}",
     "model": "anthropic/claude-sonnet-4-5"},
    {"name": "提示词优化器", "description": "优化提示词以获得更好的 AI 输出", "category": "meta",
     "content": "请优化以下提示词，使其更清晰、更具体、更有效：\n1. 明确角色和职责\n2. 细化输出格式要求\n3. 添加约束条件\n4. 包含示例（如适用）\n\n原始提示词：\n{prompt}\n\n优化后的提示词：",
     "model": "anthropic/claude-haiku-4-5"},
    {"name": "多语言翻译专家", "description": "高质量中英文互译", "category": "meta",
     "content": "你是专业翻译，请将以下内容翻译为{target_lang}。\n要求：\n1. 保持原文语气和风格\n2. 专业术语准确\n3. 符合目标语言的表达习惯\n4. 保持格式一致\n\n原文：\n{text}",
     "model": None},
]

KNOWLEDGE_BASES = [
    {"name": "产品文档", "description": "产品需求文档、设计稿、用户手册等"},
    {"name": "技术文档", "description": "架构设计、API 文档、开发规范等"},
    {"name": "运营资料", "description": "运营策略、数据分析报告、市场调研等"},
]

ASSETS = [
    {"kb_name": "产品文档", "name": "PRD-用户认证模块.md", "asset_type": "document",
     "content": "# 用户认证模块 PRD\n\n## 1. 背景\n为满足企业级安全需求，需要实现完整的用户认证和授权系统。\n\n## 2. 功能需求\n### 2.1 注册登录\n- 支持邮箱注册\n- 支持第三方 OAuth 登录\n- 密码强度校验\n- 登录失败5次锁定30分钟\n\n### 2.2 权限管理\n- RBAC 角色权限模型\n- 支持自定义角色\n- API 级别权限控制"},
    {"kb_name": "产品文档", "name": "用户画像分析报告.md", "asset_type": "document",
     "content": "# 用户画像分析报告\n\n## 核心用户群体\n1. 企业开发者（60%）：关注 API 集成和安全性\n2. 数据分析师（25%）：关注数据可视化和报告\n3. 项目经理（15%）：关注协作和进度跟踪\n\n## 使用场景\n- 日常代码审查和测试\n- 知识库文档检索\n- 自动化报告生成"},
    {"kb_name": "技术文档", "name": "API-接口规范.md", "asset_type": "document",
     "content": "# API 接口规范\n\n## RESTful 设计原则\n1. 使用标准 HTTP 方法（GET/POST/PUT/DELETE）\n2. 资源命名使用复数名词\n3. 状态码语义化\n4. 分页使用 cursor-based 方式\n\n## 认证方式\n- JWT Bearer Token\n- OAuth 2.0\n- API Key（仅限内部服务）\n\n## 响应格式\n```json\n{\"code\": 0, \"message\": \"success\", \"data\": {...}}\n```"},
    {"kb_name": "技术文档", "name": "数据库设计文档.md", "asset_type": "document",
     "content": "# 数据库设计文档\n\n## 技术栈\n- PostgreSQL 16 + pgvector\n- Redis 7（缓存/会话）\n\n## 核心表\n### users\n- id, email, username, password_hash\n- is_active, is_verified\n- auth_provider, auth_provider_id\n\n### sessions\n- id, title, user_id, kind\n- is_pinned, created_at\n\n### project_runs\n- id, session_id, requirement\n- status, approved, content_type"},
    {"kb_name": "运营资料", "name": "Q3运营策略.md", "asset_type": "document",
     "content": "# Q3 运营策略\n\n## 目标\n- MAU 提升至 5000+\n- 用户留存率 > 40%\n- NPS 评分 > 30\n\n## 关键举措\n1. 内容营销：每周发布技术博客\n2. 社区运营：建立开发者社区\n3. 产品迭代：根据用户反馈快速迭代\n4. 合作推广：与技术社区合作"},
    {"kb_name": "运营资料", "name": "竞品分析报告.md", "asset_type": "document",
     "content": "# 竞品分析报告\n\n## 竞品概览\n| 产品 | 定价 | 核心优势 | 不足 |\n|------|------|---------|------|\n| 竞品A | $29/月 | 界面友好 | 功能较少 |\n| 竞品B | $49/月 | 功能全面 | 价格偏高 |\n| 竞品C | 免费 | 开源 | 需自部署 |\n\n## 差异化策略\n- 企业级安全特性\n- 本地化部署支持\n- 灵活的定价模式"},
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

    # ── Seed prompts ──
    async with factory() as session:
        from orm.prompt_db import PromptDB
        r = await session.execute(select(PromptDB))
        existing = {p.name for p in r.scalars().all()}
        count = 0
        for p in PROMPTS:
            if p["name"] in existing:
                continue
            session.add(PromptDB(
                name=p["name"], description=p["description"], category=p["category"],
                content=p["content"], model=p["model"], status="enabled",
                version="v1.0.0", owner_id=admin_id,
            ))
            count += 1
        await session.commit()
        print(f"✅ Prompts: {count} created, {len(PROMPTS) - count} skipped (existing)")

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
            new_kb = KnowledgeBaseDB(user_id=admin_id, name=kb["name"], description=kb["description"])
            session.add(new_kb)
            await session.flush()
            kb_id_map[kb["name"]] = new_kb.id
            count += 1
        await session.commit()
        print(f"✅ Knowledge Bases: {count} created, {len(KNOWLEDGE_BASES) - count} skipped")

    # ── Seed assets (create placeholder files + DB entries) ──
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
            session.add(AssetDB(
                user_id=admin_id, name=a["name"], asset_type=a["asset_type"],
                size_bytes=len(a["content"].encode()), storage_path=file_path,
                source="upload", knowledge_base_id=kb_id, indexed=False,
            ))
            count += 1
        await session.commit()
        print(f"✅ Assets: {count} created, {len(ASSETS) - count} skipped")

    print("\n🎉 Seed complete! Refresh the admin pages to see data.")


if __name__ == "__main__":
    asyncio.run(main())
