"""Seed realistic monitoring data — clears old chart data, injects 7 days.

Covers all three sources behind the quality monitoring page:
- retrieval_logs   → volume / hits / latency / empty-recall trends + top queries
- feedback_logs    → good-rate stats + conversion funnel + review queue
- feedback_reviews → root-cause pareto + triage mix

Usage: .venv/bin/python backend/scripts/seed_monitoring.py [--days N]
"""
import asyncio
import os
import random
import sys
from datetime import UTC, datetime, timedelta
from uuid import uuid4

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend", "src"))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/ragbase")

from core.infra.database import get_session_factory
from orm.auth import UserDB
from orm.infra import FeedbackLog, FeedbackReviewDB, RetrievalLogDB
from sqlalchemy import delete, select

random.seed(42)

# 正常查询：围绕种子知识库的真实话题，命中 3~5，延迟健康。
NORMAL_QUERIES = [
    "用户认证模块的密码强度校验规则是什么",
    "RBAC 角色权限模型怎么设计",
    "API 接口规范的认证方式有哪些",
    "cursor-based 分页和 offset 分页的区别",
    "数据库设计文档里 sessions 表的结构",
    "project_runs 的 status 字段有哪些取值",
    "用户画像分析报告的核心用户群体是哪些",
    "数据分析师用户的占比是多少",
    "Q3 运营策略的 MAU 目标是多少",
    "竞品 A 和竞品 B 的定价差异",
    "知识库检索的相似度阈值如何设置",
    "JWT Bearer Token 的过期时间配置",
    "NPS 指标的计算方法",
    "OAuth 第三方登录的接入流程",
    "技术文档的开发规范在哪里",
]

# 语料缺口查询：反复出现、零召回 —— Top10 零召回切片的数据源。
GAP_QUERIES = [
    ("差旅报销流程和审批时限", 6),
    ("公司2026年节假日安排", 5),
    ("员工社保公积金缴纳比例", 4),
    ("会议室预订系统入口", 3),
    ("年度体检套餐选择", 2),
]

# 性能热点查询：高延迟（部分突破 8s SLO）—— Top10 最慢切片 + 延迟告警带。
SLOW_QUERIES = [
    "对比Q2和Q3所有运营指标的差异并输出综合趋势分析报告",
    "把产品文档、技术文档里的安全相关要求汇总成一份合规清单",
    "根据用户画像和竞品分析给出下半年的定价调整建议方案",
]


def diurnal_weight(hour: int) -> float:
    """工作时间流量权重曲线：9–12 与 14–18 高峰。"""
    if 9 <= hour <= 11 or 14 <= hour <= 17:
        return 1.0
    if hour in (12, 13) or 18 <= hour <= 21:
        return 0.5
    return 0.15


def build_retrievals(days: int):
    """生成检索日志：(created_at, query, hit_count, latency_ms)。"""
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    rows = []
    for d in range(days):
        day = now - timedelta(days=d)
        for hour in range(24):
            w = diurnal_weight(hour)
            n = int(random.gauss(4 * w + 0.5, 1.2))
            ts_base = day.replace(hour=hour)
            for _ in range(max(n, 0)):
                created = ts_base + timedelta(
                    minutes=random.randint(0, 59), seconds=random.randint(0, 59)
                )
                roll = random.random()
                if roll < 0.09:  # 语料缺口 → 零召回
                    query = random.choices(
                        [g[0] for g in GAP_QUERIES],
                        weights=[g[1] for g in GAP_QUERIES],
                    )[0]
                    hit_count, latency = 0, random.randint(180, 600)
                elif roll < 0.13:  # 复杂长尾查询 → 高延迟热点
                    query = random.choice(SLOW_QUERIES)
                    hit_count = random.randint(3, 5)
                    latency = random.randint(8500, 12500)
                else:  # 常规查询
                    query = random.choice(NORMAL_QUERIES)
                    hit_count = max(0, int(random.gauss(4, 1)))
                    latency = int(random.gauss(700, 260))
                rows.append((created, query, hit_count, max(latency, 120)))
    return rows


BAD_ANSWER_TEMPLATES = [
    "抱歉，我在知识库中没有找到与该问题直接相关的内容……",
    "根据检索到的片段，该问题涉及的内容似乎不在当前文档范围内。",
    "以上回答基于部分匹配的段落整理，可能不完整。",
]


def build_feedback(retrievals, good_ratio=0.86, rated_ratio=0.55):
    """从检索日志抽样生成评价：返回 (feedback_rows, bad_feedback_ids)。"""
    feedback_rows, bad_ids = [], []
    for idx, (created, query, hit_count, _) in enumerate(retrievals):
        # 零召回的结果更容易招差评；有命中的大部分好评。
        if hit_count == 0:
            rated, good = True, random.random() > 0.65
        else:
            rated = random.random() < rated_ratio
            good = rated and random.random() < good_ratio
        if not rated:
            continue
        rating = "good" if good else "bad"
        answer = (
            f"基于知识库检索结果，关于「{query[:20]}…」的回答正文。" if good
            else random.choice(BAD_ANSWER_TEMPLATES)
        )
        fid = str(uuid4())
        feedback_rows.append(
            {
                "id": fid,
                "run_id": str(uuid4()),
                "query": query,
                "answer": answer,
                "rating": rating,
                "created": created + timedelta(seconds=random.randint(30, 600)),
                "empty": hit_count == 0,
                "idx": idx,
            }
        )
        if not good:
            bad_ids.append(fid)
    return feedback_rows, bad_ids


def build_reviews(bad_ids, user_id):
    """差评人工分诊：约半数已处理（retrieval_miss 占主导），其余待审。"""
    reviews = []
    causes = (
        ["retrieval_miss"] * 8 + ["wrong_answer"] * 3 + ["bad_format"] * 2 + ["other"]
    )
    for fid in bad_ids:
        roll = random.random()
        if roll < 0.50:
            reviews.append(
                {
                    "feedback_id": fid,
                    "user_id": user_id,
                    "root_cause": random.choice(causes),
                    "status": "resolved",
                    "note": None,
                }
            )
        elif roll < 0.62:
            reviews.append(
                {
                    "feedback_id": fid,
                    "user_id": user_id,
                    "root_cause": None,
                    "status": "dismissed",
                    "note": "重复反馈，忽略",
                }
            )
        # 其余保持 pending（无 review 记录）
    return reviews


async def main():
    days = int(sys.argv[sys.argv.index("--days") + 1]) if "--days" in sys.argv else 7

    factory = get_session_factory()
    async with factory() as session:
        admin = (
            await session.execute(select(UserDB).where(UserDB.username == "admin"))
        ).scalar_one_or_none()
        if not admin:
            print("❌ Admin user not found. Run the app first to seed it.")
            return
        admin_id = admin.id
        print(f"✅ Found admin user: {admin.username} ({admin_id})")

    # ── 清空旧监控数据（外键顺序：reviews → logs）──
    async with factory() as session:
        r1 = await session.execute(delete(FeedbackReviewDB))
        r2 = await session.execute(delete(FeedbackLog))
        r3 = await session.execute(delete(RetrievalLogDB))
        await session.commit()
        # session.execute(delete(...)) 运行时返回 CursorResult（有 rowcount），
        # 静态签名是 Result[Any]，与 tests/conftest.py 的 ignore 约定一致。
        print(f"🗑️  Cleared: {r3.rowcount} retrievals, {r2.rowcount} feedback, {r1.rowcount} reviews")  # type: ignore[attr-defined]

    retrievals = build_retrievals(days)
    feedback_rows, bad_ids = build_feedback(retrievals)
    reviews = build_reviews(bad_ids, admin_id)

    async with factory() as session:
        session.add_all(
            RetrievalLogDB(
                id=str(uuid4()),
                user_id=admin_id,
                query=q,
                hit_count=h,
                latency_ms=latency_ms,
                top_k=5,
                created_at=c,
            )
            for c, q, h, latency_ms in retrievals
        )
        await session.commit()

        session.add_all(
            FeedbackLog(
                id=f["id"],
                run_id=f["run_id"],
                user_id=admin_id,
                rating=f["rating"],
                query=f["query"],
                answer=f["answer"],
                created_at=f["created"],
            )
            for f in feedback_rows
        )
        await session.commit()

        session.add_all(FeedbackReviewDB(**r) for r in reviews)
        await session.commit()

    span_days = days
    print(
        f"🌱 Seeded {span_days}d: {len(retrievals)} retrievals · "
        f"{len(feedback_rows)} feedback ({len(bad_ids)} bad) · {len(reviews)} reviews"
    )
    print("🎉 Monitoring seed complete! Open 质量监控 to see the charts.")


if __name__ == "__main__":
    asyncio.run(main())
