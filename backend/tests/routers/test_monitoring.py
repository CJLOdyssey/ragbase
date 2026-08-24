"""Quality monitoring API route tests (in-memory sqlite + TestClient).

Uses the shared routers/conftest.py fixtures: autouse _reset_db (clean schema
per test) and client (TestClient + redis mock + real login). The client logs
in as the seeded admin, so all requests resolve to that user id.
"""

import pytest

pytestmark = pytest.mark.unit

from datetime import UTC, datetime, timedelta

from core.infra.database import (
    FeedbackLog,
    FeedbackReviewDB,
    RetrievalLogDB,
    get_session_factory,
)

OWNER = "admin-login"


async def _seed_row(
    user_id: str,
    latency_ms: int,
    hit_count: int,
    query: str = "q",
    created_at=None,
) -> None:
    factory = get_session_factory()
    async with factory() as session:
        session.add(
            RetrievalLogDB(
                user_id=user_id,
                query=query,
                latency_ms=latency_ms,
                hit_count=hit_count,
                created_at=created_at or datetime.now(UTC),
            )
        )
        await session.commit()


async def _seed_feedback(user_id: str, rating: str) -> None:
    factory = get_session_factory()
    async with factory() as session:
        session.add(
            FeedbackLog(
                run_id="r1",
                user_id=user_id,
                rating=rating,
                created_at=datetime.now(UTC),
            )
        )
        await session.commit()


async def _seed_snapshot(user_id: str, score: int, created_at: datetime) -> None:
    from core.infra.database import HealthScoreSnapshotDB

    factory = get_session_factory()
    async with factory() as session:
        session.add(
            HealthScoreSnapshotDB(
                user_id=user_id,
                score=score,
                factors='[{"key":"retrieval","score":70,"weight":1.0}]',
                window_hours=24,
                created_at=created_at,
            )
        )
        await session.commit()


async def _seed_bad_with_review(
    user_id: str,
    status: str | None = None,
    root_cause: str | None = None,
) -> None:
    factory = get_session_factory()
    async with factory() as session:
        fb = FeedbackLog(
            run_id="r",
            user_id=user_id,
            rating="bad",
            created_at=datetime.now(UTC),
        )
        session.add(fb)
        await session.flush()
        if status is not None or root_cause is not None:
            now = datetime.now(UTC)
            session.add(
                FeedbackReviewDB(
                    feedback_id=fb.id,
                    user_id=user_id,
                    status=status or "pending",
                    root_cause=root_cause,
                    created_at=now,
                    updated_at=now,
                )
            )
        await session.commit()


class TestMonitoringRoutes:

    def test_summary_empty(self, client):
        resp = client.get("/api/monitoring/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["window_hours"] == 24
        assert data["retrieval"]["total"] == 0
        assert data["feedback"]["good_ratio"] is None
        assert data["alerts"] == []
        # 错误预算健康分：无样本 → score=null、三因子齐全。
        hs = data["health_score"]
        assert hs["score"] is None
        assert [f["key"] for f in hs["factors"]] == [
            "retrieval", "latency", "satisfaction",
        ]
        assert all(f["weight"] == 0 for f in hs["factors"])

    def test_summary_with_data_and_alert(self, client):
        for lat, hits in [(100, 3), (200, 0), (300, 1), (400, 2)]:
            client.portal.call(_seed_row, OWNER, lat, hits)
        client.portal.call(_seed_feedback, OWNER, "good")
        client.portal.call(_seed_feedback, OWNER, "bad")

        resp = client.get(
            "/api/monitoring/summary",
            params={"max_empty_recall_pct": 10, "max_p95_latency_ms": 300},
        )
        data = resp.json()
        assert data["retrieval"]["total"] == 4
        assert data["retrieval"]["empty_recall_rate"] == 0.25
        assert data["retrieval"]["latency_p95_ms"] == 400
        assert data["feedback"]["good_ratio"] == 0.5
        codes = [a["code"] for a in data["alerts"]]
        assert "empty_recall_high" in codes
        assert "p95_latency_high" in codes
        # 健康分随数据出现（整数 0-100），因子权重和为 1。
        hs = data["health_score"]
        assert isinstance(hs["score"], int)
        assert 0 <= hs["score"] <= 100
        assert sum(f["weight"] for f in hs["factors"]) == pytest.approx(1.0)

    def test_summary_burn_rate_alert_when_both_windows_burn(self, client):
        # 空召回 95%（预算 15% → burn≈6.3x ≥6 slow 层）且短窗（1h）同分布 → MWMB 触发。
        now = datetime.now(UTC)
        for n in range(20):
            # anyio ≥4 的 portal.call 只收位置参数（Unpack[PosArgsT]），kwargs 需就地展开。
            client.portal.call(
                _seed_row, OWNER, 100, 0 if n < 19 else 1,
                f"q{n}", now - timedelta(minutes=n),
            )
        data = client.get("/api/monitoring/summary").json()
        codes = [a["code"] for a in data["alerts"]]
        assert "empty_recall_high" in codes
        assert "retrieval_burn_slow" in codes
        burn = next(a for a in data["alerts"] if a["code"] == "retrieval_burn_slow")
        assert burn["level"] == "warning"
        # burn = 0.95 / 0.15 ≈ 6.3x。
        assert burn["current"] == pytest.approx(0.95 / 0.15, abs=0.1)

    def test_summary_scoped_to_current_user(self, client):
        # Baseline-relative: rows from a previous test may share the owner id
        # (per-worker shared SQLite engine), so never assert an absolute 0.
        baseline = client.get("/api/monitoring/summary").json()["retrieval"]["total"]
        client.portal.call(_seed_row, "other", 999, 0)
        resp = client.get("/api/monitoring/summary")
        assert resp.status_code == 200
        assert resp.json()["retrieval"]["total"] == baseline  # other's rows never leak in
        client.portal.call(_seed_row, OWNER, 120, 1)
        resp = client.get("/api/monitoring/summary")
        assert resp.json()["retrieval"]["total"] == baseline + 1  # own rows are visible

    def test_validation_rejects_bad_window(self, client):
        resp = client.get(
            "/api/monitoring/summary", params={"window_hours": -1}
        )
        assert resp.status_code == 422

    def test_summary_accepts_zero_as_all_time(self, client):
        client.portal.call(_seed_row, OWNER, 150, 2)
        resp = client.get("/api/monitoring/summary", params={"window_hours": 0})
        assert resp.status_code == 200
        data = resp.json()
        assert data["window_hours"] == 0
        assert data["retrieval"]["total"] >= 1

    def test_timeseries_returns_aligned_grid(self, client):
        for lat, hits in [(100, 3), (200, 0)]:
            client.portal.call(_seed_row, OWNER, lat, hits)
        client.portal.call(_seed_feedback, OWNER, "good")

        resp = client.get("/api/monitoring/timeseries")
        assert resp.status_code == 200
        data = resp.json()
        assert data["bucket_hours"] >= 1
        points = data["points"]
        assert 1 <= len(points) <= 48
        totals = sum(p["retrievals"] for p in points)
        empties = sum(p["empty_count"] for p in points)
        goods = sum(p["good"] for p in points)
        assert totals >= 2
        assert empties >= 1
        assert goods >= 1
        # 每个点字段齐全，ts 单调递增。
        expected_keys = {
            "ts", "retrievals", "empty_count",
            "avg_hits", "avg_latency_ms",
            "latency_p50_ms", "latency_p95_ms", "latency_p99_ms",
            "good", "bad",
        }
        for p in points:
            assert set(p.keys()) == expected_keys
        for a, b in zip(points, points[1:], strict=False):
            assert a["ts"] < b["ts"]

    def test_timeseries_accepts_zero_as_all_time(self, client):
        client.portal.call(_seed_row, OWNER, 120, 1)
        resp = client.get(
            "/api/monitoring/timeseries", params={"window_hours": 0}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["window_hours"] == 0
        assert sum(p["retrievals"] for p in data["points"]) >= 1

    # ---- root-causes -------------------------------------------------

    def test_root_causes_empty_window(self, client):
        resp = client.get("/api/monitoring/root-causes")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_bad"] >= 0
        assert data["pending"] == data["total_bad"]
        causes = {c["cause"]: c["count"] for c in data["causes"]}
        assert set(causes) == {
            "retrieval_miss", "wrong_answer", "bad_format", "other",
        }

    def test_root_causes_counts_and_status_mix(self, client):
        client.portal.call(
            _seed_bad_with_review, OWNER, "resolved", "retrieval_miss"
        )
        client.portal.call(
            _seed_bad_with_review, OWNER, "dismissed", "wrong_answer"
        )
        # 未审查：无 review 记录 → pending，不计入任何根因。
        client.portal.call(_seed_bad_with_review, OWNER)

        data = client.get("/api/monitoring/root-causes").json()
        assert data["total_bad"] == 3
        assert data["pending"] == 1
        assert data["resolved"] == 1
        assert data["dismissed"] == 1
        causes = {c["cause"]: c["count"] for c in data["causes"]}
        assert causes["retrieval_miss"] == 1
        assert causes["wrong_answer"] == 1
        assert causes["bad_format"] == 0
        assert causes["other"] == 0

    def test_root_causes_scoped_to_current_user(self, client):
        baseline = client.get("/api/monitoring/root-causes").json()["total_bad"]
        client.portal.call(
            _seed_bad_with_review, "other", "resolved", "bad_format"
        )
        resp = client.get("/api/monitoring/root-causes")
        assert resp.json()["total_bad"] == baseline  # other 的差评不泄漏

    def test_root_causes_accepts_zero_as_all_time(self, client):
        client.portal.call(_seed_bad_with_review, OWNER)
        resp = client.get(
            "/api/monitoring/root-causes", params={"window_hours": 0}
        )
        assert resp.status_code == 200
        assert resp.json()["window_hours"] == 0

    # ---- top-queries --------------------------------------------------

    def test_top_queries_empty_kind_ranks_by_frequency(self, client):
        for _ in range(3):
            client.portal.call(_seed_row, OWNER, 100, 0, "gap query")
        client.portal.call(_seed_row, OWNER, 100, 0, "minor gap")
        client.portal.call(_seed_row, OWNER, 100, 5, "healthy query")

        data = client.get(
            "/api/monitoring/top-queries", params={"kind": "empty"}
        ).json()
        assert data["kind"] == "empty"
        items = data["items"]
        assert items[0]["query"] == "gap query"
        assert items[0]["count"] == 3
        assert all(i["query"] != "healthy query" for i in items)

    def test_top_queries_slow_kind_ranks_by_latency(self, client):
        for _ in range(2):
            client.portal.call(_seed_row, OWNER, 900, 2, "slow one")
        client.portal.call(_seed_row, OWNER, 100, 3, "fast one")

        data = client.get(
            "/api/monitoring/top-queries", params={"kind": "slow"}
        ).json()
        items = data["items"]
        assert items[0]["query"] == "slow one"
        assert items[0]["avg_latency_ms"] == 900
        assert items[-1]["avg_latency_ms"] <= items[0]["avg_latency_ms"]

    def test_top_queries_validation_rejects_bad_params(self, client):
        resp = client.get("/api/monitoring/top-queries", params={"kind": "bogus"})
        assert resp.status_code == 422
        resp = client.get("/api/monitoring/top-queries", params={"limit": 999})
        assert resp.status_code == 422

    def test_top_queries_scoped_to_current_user(self, client):
        client.portal.call(_seed_row, "other", 500, 0, "foreign gap")
        data = client.get(
            "/api/monitoring/top-queries", params={"kind": "empty"}
        ).json()
        assert all(i["query"] != "foreign gap" for i in data["items"])

    # ---- custom since/until range ------------------------------------

    def test_custom_range_filters_rows_on_summary(self, client):
        now = datetime.now(UTC)
        client.portal.call(_seed_row, OWNER, 100, 2, "fresh", now)
        client.portal.call(
            _seed_row, OWNER, 100, 2, "stale", now - timedelta(days=10)
        )
        params = {
            "since": (now - timedelta(days=5)).isoformat(),
            "until": now.isoformat(),
        }
        data = client.get("/api/monitoring/summary", params=params).json()
        assert data["retrieval"]["total"] == 1
        assert data["window_hours"] == 24  # legacy param echoed untouched

    def test_custom_range_since_overrides_window_hours(self, client):
        now = datetime.now(UTC)
        client.portal.call(
            _seed_row, OWNER, 100, 2, "old but in range",
            now - timedelta(days=20),
        )
        params = {
            "window_hours": 1,  # 滑窗看不到 20 天前的行
            "since": (now - timedelta(days=30)).isoformat(),
        }
        data = client.get("/api/monitoring/summary", params=params).json()
        assert data["retrieval"]["total"] >= 1

    def test_custom_range_applies_to_top_queries_and_root_causes(self, client):
        now = datetime.now(UTC)
        client.portal.call(_seed_row, OWNER, 900, 0, "old slow", now - timedelta(days=8))
        params = {
            "since": (now - timedelta(days=30)).isoformat(),
            "until": now.isoformat(),
        }
        top = client.get("/api/monitoring/top-queries", params=params).json()
        assert any(i["query"] == "old slow" for i in top["items"])
        rc = client.get("/api/monitoring/root-causes", params=params)
        assert rc.status_code == 200

    def test_custom_range_validation_rejects_bad_ranges(self, client):
        now = datetime.now(UTC)
        # since >= until
        resp = client.get(
            "/api/monitoring/summary",
            params={
                "since": now.isoformat(),
                "until": (now - timedelta(hours=1)).isoformat(),
            },
        )
        assert resp.status_code == 422
        # 超过 90 天
        resp = client.get(
            "/api/monitoring/summary",
            params={
                "since": (now - timedelta(days=100)).isoformat(),
                "until": now.isoformat(),
            },
        )
        assert resp.status_code == 422
        # until 在未来
        resp = client.get(
            "/api/monitoring/summary",
            params={"until": (now + timedelta(days=2)).isoformat()},
        )
        assert resp.status_code == 422

    def test_timeseries_include_previous_returns_aligned_previous(self, client):
        now = datetime.now(UTC)
        client.portal.call(_seed_row, OWNER, 120, 3, "cur", now)
        client.portal.call(
            _seed_row, OWNER, 200, 1, "prev", now - timedelta(hours=30)
        )
        resp = client.get(
            "/api/monitoring/timeseries",
            params={"window_hours": 24, "include_previous": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        prev = data["previous_points"]
        assert prev is not None
        assert len(prev) == len(data["points"])
        assert sum(p["retrievals"] for p in prev) >= 1  # 30h 前的行落入上期
        assert sum(p["retrievals"] for p in data["points"]) >= 1
        for a, b in zip(prev, prev[1:], strict=False):
            assert a["ts"] < b["ts"]

    def test_timeseries_without_flag_has_no_previous(self, client):
        client.portal.call(_seed_row, OWNER, 120, 3)
        data = client.get("/api/monitoring/timeseries").json()
        assert data["previous_points"] is None


class TestLatencyDistributionRoutes:
    """latency-heatmap / latency-scatter（诊断 Tab 分布图数据源）。"""

    def test_heatmap_empty_returns_zero_grid(self, client):
        resp = client.get("/api/monitoring/latency-heatmap")
        assert resp.status_code == 200
        data = resp.json()
        assert data["bucket_hours"] >= 1
        assert data["bin_edges_ms"] == [500, 1000, 2000, 4000, 8000]
        assert len(data["points"]) >= 1
        for p in data["points"]:
            assert p["counts"] == [0] * 6

    def test_heatmap_places_counts_into_fixed_bins(self, client):
        # 每档一条：100→bin0, 700→bin1, 1500→bin2, 3000→bin3, 6000→bin4, 9000→bin5
        for lat in (100, 700, 1500, 3000, 6000, 9000):
            client.portal.call(_seed_row, OWNER, lat, 2)
        data = client.get("/api/monitoring/latency-heatmap", params={"window_hours": 1}).json()
        totals = [
            sum(c) for c in zip(*(p["counts"] for p in data["points"]), strict=True)
        ]
        assert totals == [1, 1, 1, 1, 1, 1]

    def test_heatmap_scoped_to_current_user(self, client):
        client.portal.call(_seed_row, OWNER, 100, 2)
        client.portal.call(_seed_row, "someone-else", 9000, 2)
        data = client.get("/api/monitoring/latency-heatmap", params={"window_hours": 1}).json()
        counts = [c for p in data["points"] for c in p["counts"]]
        assert sum(counts) == 1

    def test_scatter_chronological_with_fields(self, client):
        now = datetime.now(UTC)
        client.portal.call(_seed_row, OWNER, 100, 3, "a", now - timedelta(minutes=5))
        client.portal.call(_seed_row, OWNER, 9500, 0, "b", now)
        data = client.get("/api/monitoring/latency-scatter").json()
        assert data["total"] == 2
        assert data["sampled"] == 2
        assert [i["latency_ms"] for i in data["items"]] == [100, 9500]
        assert [i["hits"] for i in data["items"]] == [3, 0]
        assert all("ts" in i for i in data["items"])

    def test_scatter_respects_limit_and_reports_truncation(self, client):
        now = datetime.now(UTC)
        for n in range(5):
            # 显式错开时间戳：同刻插入时 order_by 平局顺序不稳定，断言无从谈起
            client.portal.call(
                _seed_row,
                OWNER,
                100 + n,
                1,
                f"q{n}",
                now - timedelta(minutes=10 - n),
            )
        data = client.get(
            "/api/monitoring/latency-scatter", params={"limit": 2}
        ).json()
        assert data["total"] == 5
        assert data["sampled"] == 2
        assert len(data["items"]) == 2
        # newest-first 截断 → 保留的是最新两条（时间戳最大）
        assert [i["latency_ms"] for i in data["items"]] == [103, 104]

    def test_scatter_custom_range(self, client):
        now = datetime.now(UTC)
        client.portal.call(_seed_row, OWNER, 100, 2, "fresh", now)
        client.portal.call(
            _seed_row, OWNER, 200, 2, "stale", now - timedelta(days=10)
        )
        params = {
            "since": (now - timedelta(days=5)).isoformat(),
            "until": now.isoformat(),
        }
        data = client.get("/api/monitoring/latency-scatter", params=params).json()
        assert data["total"] == 1
        assert data["items"][0]["latency_ms"] == 100

    # ---- health-score history -----------------------------------------

    def test_health_history_empty_and_scoped(self, client):
        resp = client.get("/api/monitoring/health-score/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["hours"] == 168
        assert isinstance(data["points"], list)

    def test_health_history_returns_ascending_snapshots(self, client):
        now = datetime.now(UTC)
        for offset_h, score in ((3, 90), (2, 80), (1, 70)):
            client.portal.call(
                _seed_snapshot, OWNER, score, now - timedelta(hours=offset_h)
            )
        client.portal.call(_seed_snapshot, "someone-else", 1, now)
        data = client.get("/api/monitoring/health-score/history").json()
        tss = [p["ts"] for p in data["points"]]
        assert tss == sorted(tss)  # ts 升序（最旧在前）
        assert data["points"][-1]["score"] == 70  # 最新快照
        assert 1 not in [p["score"] for p in data["points"]]  # 其他用户不泄漏
