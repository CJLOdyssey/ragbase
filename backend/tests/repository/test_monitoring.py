"""Online quality monitoring repository tests (unit, in-memory sqlite)."""

from datetime import UTC, datetime, timedelta

from core.infra.database import FeedbackLog, RetrievalLogDB, get_session_factory
from repository.monitoring import (
    evaluate_alerts,
    feedback_summary,
    retrieval_summary,
)
from repository.monitoring_shared import percentile_nearest_rank


async def _seed_retrieval(rows: list[dict]) -> None:
    factory = get_session_factory()
    async with factory() as session:
        for r in rows:
            session.add(
                RetrievalLogDB(
                    id=r.get("id"),
                    user_id=r.get("user_id", "u1"),
                    session_id=r.get("session_id"),
                    query=r.get("query", "q"),
                    top_k=r.get("top_k", 5),
                    rerank=r.get("rerank", False),
                    min_score=r.get("min_score"),
                    latency_ms=r["latency_ms"],
                    hit_count=r["hit_count"],
                    created_at=r.get("created_at", datetime.now(UTC)),
                )
            )
        await session.commit()


async def _seed_feedback(ratings: list[str], user_id: str = "u1") -> None:
    factory = get_session_factory()
    async with factory() as session:
        for rating in ratings:
            session.add(
                FeedbackLog(
                    run_id="r1",
                    user_id=user_id,
                    rating=rating,
                    created_at=datetime.now(UTC),
                )
            )
        await session.commit()


class TestRetrievalSummary:
    async def test_empty_db(self):
        summary = await retrieval_summary("u1", 24)
        assert summary == {
            "total": 0,
            "empty_recall_count": 0,
            "empty_recall_rate": 0.0,
            "slow_count": 0,
            # 错误预算维度：超 SLO 请求占比（无样本时 0.0，与空召回率约定一致）。
            "slow_rate": 0.0,
            "avg_hit_count": None,
            "latency_p50_ms": None,
            "latency_p95_ms": None,
            # 分支新增 p99 分位后 summary 的完整契约
            "latency_p99_ms": None,
        }

    async def test_aggregates_rate_and_percentiles(self):
        await _seed_retrieval(
            [
                {"latency_ms": 100, "hit_count": 3},
                {"latency_ms": 200, "hit_count": 0},
                {"latency_ms": 300, "hit_count": 1},
                {"latency_ms": 400, "hit_count": 2},
            ]
        )
        summary = await retrieval_summary("u1", 24)
        assert summary["total"] == 4
        assert summary["empty_recall_count"] == 1
        assert summary["empty_recall_rate"] == 0.25
        assert summary["slow_count"] == 0
        assert summary["slow_rate"] == 0.0
        assert summary["latency_p50_ms"] == 200
        assert summary["latency_p95_ms"] == 400

    async def test_slow_rate_counts_above_slo_boundary(self):
        await _seed_retrieval(
            [
                {"latency_ms": 100, "hit_count": 1},
                {"latency_ms": 8000, "hit_count": 1},   # 恰在 SLO 上不计慢
                {"latency_ms": 8001, "hit_count": 1},   # >SLO 计慢
                {"latency_ms": 9000, "hit_count": 1},
            ]
        )
        summary = await retrieval_summary("u1", 24)
        assert summary["slow_count"] == 2
        assert summary["slow_rate"] == 0.5

    async def test_custom_latency_slo_threshold(self):
        await _seed_retrieval(
            [
                {"latency_ms": 100, "hit_count": 1},
                {"latency_ms": 500, "hit_count": 1},
            ]
        )
        summary = await retrieval_summary("u1", 24, latency_slo_ms=300)
        assert summary["slow_count"] == 1
        assert summary["slow_rate"] == 0.5

    async def test_scoped_to_user_and_window(self):
        await _seed_retrieval(
            [
                {"user_id": "u2", "latency_ms": 999, "hit_count": 0},
                {"latency_ms": 10, "hit_count": 1},
                {
                    "latency_ms": 20,
                    "hit_count": 1,
                    "created_at": datetime.now(UTC) - timedelta(hours=48),
                },
            ]
        )
        summary = await retrieval_summary("u1", 24)
        assert summary["total"] == 1
        assert summary["latency_p50_ms"] == 10


class TestFeedbackSummary:
    async def test_empty_db(self):
        summary = await feedback_summary("u1", 24)
        assert summary == {
            "total": 0,
            "good_count": 0,
            "bad_count": 0,
            "good_ratio": None,
            "answered_runs": 0,
        }

    async def test_good_ratio(self):
        await _seed_feedback(["good", "good", "bad"])
        summary = await feedback_summary("u1", 24)
        assert summary["total"] == 3
        assert summary["good_count"] == 2
        assert summary["bad_count"] == 1
        assert summary["good_ratio"] == 2 / 3

    async def test_scoped_to_user(self):
        await _seed_feedback(["good", "good", "bad"], user_id="u2")
        summary = await feedback_summary("u1", 24)
        assert summary["total"] == 0


class TestEvaluateAlerts:
    def test_no_alerts_within_thresholds(self):
        retrieval = {"total": 10, "empty_recall_rate": 0.05, "latency_p95_ms": 3000}
        feedback = {"total": 5, "good_ratio": 0.9}
        assert evaluate_alerts(retrieval, feedback) == []

    def test_empty_recall_alert(self):
        retrieval = {"total": 10, "empty_recall_rate": 0.3, "latency_p95_ms": 100}
        feedback = {"total": 0, "good_ratio": None}
        alerts = evaluate_alerts(retrieval, feedback)
        assert [a["code"] for a in alerts] == ["empty_recall_high"]
        assert alerts[0]["current"] == 30.0
        assert alerts[0]["threshold"] == 15.0

    def test_p95_latency_alert(self):
        retrieval = {"total": 10, "empty_recall_rate": 0.0, "latency_p95_ms": 9000}
        feedback = {"total": 0, "good_ratio": None}
        alerts = evaluate_alerts(retrieval, feedback)
        assert [a["code"] for a in alerts] == ["p95_latency_high"]

    def test_good_ratio_alert(self):
        retrieval = {"total": 10, "empty_recall_rate": 0.0, "latency_p95_ms": 100}
        feedback = {"total": 4, "good_ratio": 0.4}
        alerts = evaluate_alerts(retrieval, feedback)
        assert [a["code"] for a in alerts] == ["good_ratio_low"]

    def test_multiple_alerts_and_custom_thresholds(self):
        retrieval = {"total": 5, "empty_recall_rate": 0.5, "latency_p95_ms": 12000}
        feedback = {"total": 2, "good_ratio": 0.2}
        alerts = evaluate_alerts(
            retrieval,
            feedback,
            max_empty_recall_pct=10,
            max_p95_latency_ms=1000,
            min_good_ratio=0.5,
        )
        assert [a["code"] for a in alerts] == [
            "empty_recall_high",
            "p95_latency_high",
            "good_ratio_low",
        ]

    def test_no_alert_when_no_samples(self):
        retrieval = {"total": 0, "empty_recall_rate": 0.0, "latency_p95_ms": None}
        feedback = {"total": 0, "good_ratio": None}
        assert evaluate_alerts(retrieval, feedback) == []


class TestPercentile:
    def test_nearest_rank(self):
        assert percentile_nearest_rank([1, 2, 3, 4], 50) == 2
        assert percentile_nearest_rank([1, 2, 3, 4], 95) == 4
        assert percentile_nearest_rank([5], 50) == 5

    def test_empty(self):
        assert percentile_nearest_rank([], 50) is None
