"""Error-budget health score + MWMB burn-rate alerts (pure unit tests)."""

from datetime import UTC, datetime, timedelta

import pytest

pytestmark = pytest.mark.unit

from services.health_score import (
    FAST_BURN_RATE,
    MIN_FEEDBACK_SAMPLES,
    SLOW_BURN_RATE,
    SLOW_REQUEST_BUDGET,
    compute_health_score,
    dimension_score,
    evaluate_burn_rate_alerts,
    short_window_bounds,
    wilson_lower_bound,
)


class TestDimensionScore:
    def test_no_consumption_is_full_score(self):
        assert dimension_score(0.0, 0.15) == 100

    def test_in_budget_linear_100_to_70(self):
        # x = 0.075/0.15 = 0.5 → 100 − 30×0.5 = 85
        assert dimension_score(0.075, 0.15) == 85
        # x = 1（预算恰好用尽）→ 70：<70 ⇔ 超预算 ⇔ 静态阈值告警触发
        assert dimension_score(0.15, 0.15) == 70

    def test_overspend_decays_70_to_0(self):
        # x = 1.5 → 70×(2−1.5) = 35；边际越线与灾难性越线可区分
        assert dimension_score(0.225, 0.15) == 35
        assert dimension_score(0.30, 0.15) == 0
        assert dimension_score(0.45, 0.15) == 0  # x>2 继续钳制

    def test_zero_budget_undefined(self):
        assert dimension_score(0.0, 0.0) is None


class TestWilson:
    def test_small_samples_conservative(self):
        # 2/3 的 Wilson 95% 下界 ≈ 0.207 —— 远低于原始比率。
        lb = wilson_lower_bound(2, 3)
        assert 0.15 < lb < 0.3

    def test_large_samples_converge_to_raw(self):
        assert wilson_lower_bound(9000, 10000) > 0.89

    def test_bounds_clamped(self):
        assert wilson_lower_bound(0, 5) == 0.0
        assert wilson_lower_bound(5, 5) < 1.0
        assert wilson_lower_bound(1, 0) == 0.0


def _retrieval(
    total: int = 100,
    empty_rate: float = 0.0333,
    slow_rate: float | None = 0.02,
) -> dict:
    return {
        "total": total,
        "empty_recall_rate": empty_rate,
        "slow_rate": slow_rate,
        "latency_p95_ms": 2100,
    }


def _feedback(ratio: float | None = 0.9, total: int = 40) -> dict:
    return {"total": total, "good_ratio": ratio}


class TestComputeHealthScore:
    def test_all_dimensions_budget_semantics(self):
        result = compute_health_score(_retrieval(), _feedback())
        scores = {f["key"]: f["score"] for f in result["factors"]}
        # 新分段语义 dimension_score：x=bad_rate/budget，
        # x≤1 → 100−30x；x∈(1,2] → 70(2−x)；x>2 → 0。
        # retrieval: x=0.0333/0.15≈0.222 → 93；latency: x=0.4 → 88；
        # satisfaction(total=40≥30 走原始比率): bad=0.1/budget 0.4 → x=0.25 → 92.5 → 92。
        assert scores["retrieval"] == 93
        assert scores["latency"] == 88
        assert scores["satisfaction"] == 92
        assert sum(f["weight"] for f in result["factors"]) == pytest.approx(1.0)

    def test_over_budget_factor_zeroes_out_total(self):
        result = compute_health_score(
            _retrieval(empty_rate=0.5), _feedback()
        )
        by_key = {f["key"]: f for f in result["factors"]}
        assert by_key["retrieval"]["score"] == 0  # x=3.33 > 2
        # 检索 0×0.3 + 延迟 88×0.3 + 满意度 92×0.4 = 63.2 → 63。
        assert result["score"] == 63

    def test_no_samples_anywhere_score_null(self):
        result = compute_health_score(_retrieval(total=0), _feedback(total=0))
        assert result["score"] is None
        assert all(f["weight"] == 0 for f in result["factors"])

    def test_partial_data_redistributes_weight(self):
        result = compute_health_score(
            _retrieval(total=0), _feedback()  # 检索/延迟无样本
        )
        by_key = {f["key"]: f for f in result["factors"]}
        assert by_key["retrieval"]["weight"] == 0
        assert by_key["latency"]["weight"] == 0
        assert by_key["satisfaction"]["weight"] == pytest.approx(1.0)
        assert result["score"] == 92

    def test_low_sample_feedback_dropped(self):
        result = compute_health_score(
            _retrieval(total=0),
            {"total": MIN_FEEDBACK_SAMPLES - 1, "good_ratio": 1.0},
        )
        by_key = {f["key"]: f for f in result["factors"]}
        assert by_key["satisfaction"]["score"] is None
        assert result["score"] is None  # 唯一因子被丢弃 → 总分 null

    def test_wilson_zone_conservative(self):
        raw_result = compute_health_score(
            _retrieval(total=0), _feedback(ratio=0.9, total=200)
        )
        wilson_result = compute_health_score(
            _retrieval(total=0), _feedback(ratio=0.9, total=20)
        )
        assert wilson_result["score"] is not None
        assert raw_result["score"] is not None
        # 小样本用 Wilson 下界 → 得分严格更保守。
        assert wilson_result["score"] < raw_result["score"]

    def test_slow_rate_missing_latency_factor_null(self):
        result = compute_health_score(
            _retrieval(slow_rate=None), _feedback()
        )
        by_key = {f["key"]: f for f in result["factors"]}
        assert by_key["latency"]["score"] is None


def _burn_pair(
    long_bad: float, short_bad: float, *, kind: str = "retrieval", total: int = 100
) -> tuple[dict, dict, dict, dict]:
    """(long_retrieval, long_feedback, short_retrieval, short_feedback) fixture."""
    rate_key = "empty_rate" if kind == "retrieval" else "slow_rate"
    if kind == "satisfaction":
        healthy_r = _retrieval(total=total)
        long_fb = {"total": total, "good_ratio": 1 - long_bad}
        short_fb = {"total": total, "good_ratio": 1 - short_bad}
        return healthy_r, long_fb, healthy_r, short_fb
    long_r = _retrieval(total=total, **{rate_key: long_bad})
    short_r = _retrieval(total=total, **{rate_key: short_bad})
    no_fb = _feedback(total=0)
    return long_r, no_fb, short_r, no_fb


class TestBurnRateAlerts:
    def test_fast_burn_math_check(self):
        # max_empty_recall_pct=5 → 预算 0.05；bad_rate=1.0 → burn=20 ≥14.4。
        alerts = evaluate_burn_rate_alerts(
            *_burn_pair(1.0, 1.0), max_empty_recall_pct=5.0
        )
        fast = [a for a in alerts if a["code"] == "retrieval_burn_fast"]
        assert len(fast) == 1
        assert fast[0]["level"] == "critical"
        assert fast[0]["current"] == pytest.approx(round(1.0 / 0.05, 1))
        assert fast[0]["threshold"] == FAST_BURN_RATE

    def test_slow_burn_only_when_short_window_confirms(self):
        # 预算 0.15：bad=0.93 → burn 6.2 ≥6 但 <14.4；双窗同分布 → slow 层告警。
        alerts = evaluate_burn_rate_alerts(*_burn_pair(0.93, 0.93))
        codes = [a["code"] for a in alerts]
        assert "retrieval_burn_slow" in codes
        assert "retrieval_burn_fast" not in codes

    def test_transient_spike_suppressed_by_mwmb(self):
        # 长窗高燃烧（6.2x）、短窗已恢复 → 不告警（MWMB 合取的关键价值）。
        alerts = evaluate_burn_rate_alerts(*_burn_pair(0.93, 0.01))
        assert all(not a["code"].startswith("retrieval_burn") for a in alerts)

    def test_satisfaction_dimension_burn(self):
        # 默认 60% 下限的预算(0.4)太大、燃烧率封顶 2.5x 达不到告警层——
        # 收紧下限到 90%（预算 0.1）验证满意度维度的机制本身。
        alerts = evaluate_burn_rate_alerts(
            *_burn_pair(0.99, 0.99, kind="satisfaction"), min_good_ratio=0.9
        )
        slow = [a for a in alerts if a["code"] == "satisfaction_burn_slow"]
        assert len(slow) == 1
        assert slow[0]["level"] == "warning"
        assert slow[0]["threshold"] == SLOW_BURN_RATE

    def test_no_data_windows_produce_nothing(self):
        empty = {"total": 0, "good_ratio": None}
        assert (
            evaluate_burn_rate_alerts(empty, empty, empty, empty) == []
        )

    def test_latency_dimension_uses_fixed_budget(self):
        # slow_rate 全超 → burn = 1.0/0.05 = 20 ≥ 14.4 → critical fast。
        alerts = evaluate_burn_rate_alerts(*_burn_pair(1.0, 1.0, kind="latency"))
        fast = [a for a in alerts if a["code"] == "latency_burn_fast"]
        assert len(fast) == 1
        assert fast[0]["current"] == pytest.approx(1.0 / SLOW_REQUEST_BUDGET)


class TestShortWindowBounds:
    def test_sliding_window_derives_from_now(self):
        before = datetime.now(UTC)
        pair = short_window_bounds(24, None, None)
        assert pair is not None
        since, upper = pair
        # 24h/12=2h → 上限钳到 1h。
        span_min = (upper - since).total_seconds() / 3600
        assert span_min == 1.0
        assert upper >= before

    def test_one_hour_window_hits_five_minute_floor(self):
        pair = short_window_bounds(1, None, None)
        since, upper = pair  # type: ignore[misc]
        assert (upper - since) == timedelta(minutes=5)

    def test_custom_range_anchors_on_until(self):
        until = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
        since_custom = until - timedelta(days=12)
        pair = short_window_bounds(0, since_custom, until)
        since, upper = pair  # type: ignore[misc]
        assert upper == until
        # 12d/12 = 24h，但钳制上限为 1h。
        assert (upper - since) == timedelta(hours=1)

    def test_all_time_without_bounds_returns_none(self):
        assert short_window_bounds(0, None, None) is None
