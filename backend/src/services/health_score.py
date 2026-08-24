"""Composite health score + burn-rate alerting via the error-budget model.

Aligned with Google SRE Workbook Ch.4-5: every quality dimension is modeled
as a good-events SLI guarded by an error budget. The factor score is
anchored on the consumed-budget multiple ``x = bad_rate / budget``:

    in-budget  (x ≤ 1):  score = 100 − 30x      (100 at zero consumption,
                                                 70 exactly at the threshold)
    overspent  (1 < x ≤ 2): score = 70(2 − x)   (decays to 0 at 2× budget)

The threshold anchor keeps the gauge aligned with alerting — ``score < 70``
⇔ budget exhausted ⇔ the static-threshold alert fires — while the decay
band preserves gradation for marginal breaches.

Dimensions (bad-event rate vs budget):
- retrieval    empty-recall queries      budget = max_empty_recall_pct / 100
- latency      latency > SLO queries     budget = SLOW_REQUEST_BUDGET (5%;
               "slow_rate <= 5%" is mathematically equivalent to p95 <= SLO)
- satisfaction bad ratings               budget = 1 - min_good_ratio

Low-sample feedback is stabilized before scoring: n < MIN_FEEDBACK_SAMPLES
drops the factor entirely (weight redistribution downstream); below
WILSON_MIN_SAMPLES the Wilson lower bound replaces the raw good ratio so a
handful of ratings cannot masquerade as a stable signal.

Burn-rate alerts follow multi-window multi-burn-rate (MWMB): a dimension
only alerts when BOTH the long window and its trailing short window burn
budget faster than the tier threshold — page tier FAST_BURN_RATE (14.4x),
ticket tier SLOW_BURN_RATE (6x). Pure functions only; fully unit-testable.

Adding a dimension = appending one ``_Dimension`` entry; every consumer
(score, alerts, weights) derives from that single table.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from math import sqrt
from typing import Any, NamedTuple, TypedDict

HealthFactorKey = str  # "retrieval" | "latency" | "satisfaction"


class HealthFactor(TypedDict):
    key: HealthFactorKey
    score: int | None  # null = 该因子窗口内无样本
    weight: float  # 重分配后的最终权重


class HealthScoreResult(TypedDict):
    score: int | None
    factors: list[HealthFactor]


# Latency error budget: fraction of requests allowed above the latency SLO.
# Equivalent formulation of the p95 threshold (p95 <= X  <=>  slow_rate <= 5%).
SLOW_REQUEST_BUDGET = 0.05

# Feedback stabilization (Wilson score interval at ~95% confidence).
WILSON_Z = 1.96
MIN_FEEDBACK_SAMPLES = 10
WILSON_MIN_SAMPLES = 30

# MWMB tiers from Google SRE Workbook Table 5-8 (30-day reference period).
FAST_BURN_RATE = 14.4
SLOW_BURN_RATE = 6.0

# Short-window derivation: trailing 1/12 of the long window, clamped to
# [5 minutes, 1 hour] per the workbook's k=12 heuristic.
SHORT_WINDOW_RATIO = 12.0
MIN_SHORT_WINDOW_H = 1.0 / 12.0
MAX_SHORT_WINDOW_H = 1.0


def wilson_lower_bound(good: int, total: int) -> float:
    """Lower bound of the Wilson score interval for a proportion."""
    if total <= 0:
        return 0.0
    z2 = WILSON_Z * WILSON_Z
    n = float(total)
    p = good / n
    center = (p + z2 / (2 * n)) / (1 + z2 / n)
    half = WILSON_Z * sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / (1 + z2 / n)
    return min(1.0, max(0.0, center - half))


def dimension_score(bad_rate: float, budget: float) -> int | None:
    """Error-budget score with a post-threshold decay band.

    ``x = bad_rate / budget`` is the consumed-budget multiple:
    - x ∈ [0, 1]  in-budget:      100 → 70   (score = 30 + 70 × remaining)
    - x ∈ (1, 2]  overspent:      70 → 0     (decays with overspend depth)
    - x > 2:                      0

    Invariant tying the gauge to alerting: ``score < 70`` ⇔ budget exhausted
    ⇔ the matching static-threshold alert fires. The decay band keeps a
    marginal breach (p95 slightly over SLO) visually distinct from a
    catastrophic one instead of slamming both to 0.
    """
    if budget <= 0:
        return None
    x = bad_rate / budget
    raw = (100 - 30 * x) if x <= 1 else 70 * (2 - x)
    return round(min(100.0, max(0.0, raw)))


def short_window_bounds(
    window_hours: int,
    since: datetime | None,
    until: datetime | None,
) -> tuple[datetime, datetime] | None:
    """Trailing sub-window ``(since_short, upper)`` for MWMB checks.

    Custom ``since``/``until`` anchor on ``until`` (or now); preset windows
    slide from now. All-time queries without explicit bounds have no bounded
    long window, so burn-rate checks are skipped (None).
    """
    if since is not None and until is not None:
        span_h = (until - since).total_seconds() / 3600
        upper = until
    elif window_hours > 0:
        span_h = float(window_hours)
        upper = datetime.now(UTC)
    else:
        return None
    short_h = min(MAX_SHORT_WINDOW_H, max(span_h / SHORT_WINDOW_RATIO, MIN_SHORT_WINDOW_H))
    return upper - timedelta(hours=short_h), upper


def _effective_good_ratio(total: int, good_ratio: float | None) -> float | None:
    """Raw ratio stabilized by sample size (Wilson LB in the uncertain zone)."""
    if total <= 0 or good_ratio is None:
        return None
    if total >= WILSON_MIN_SAMPLES:
        return good_ratio
    if total < MIN_FEEDBACK_SAMPLES:
        return None
    return wilson_lower_bound(round(good_ratio * total), total)


def _empty_recall_bad_rate(
    retrieval: dict[str, Any], _feedback: dict[str, Any]
) -> float | None:
    if int(retrieval.get("total") or 0) <= 0:
        return None
    value = retrieval.get("empty_recall_rate")
    return float(value) if value is not None else None


def _slow_request_bad_rate(
    retrieval: dict[str, Any], _feedback: dict[str, Any]
) -> float | None:
    if int(retrieval.get("total") or 0) <= 0:
        return None
    value = retrieval.get("slow_rate")
    return float(value) if value is not None else None


def _satisfaction_bad_rate(
    _retrieval: dict[str, Any], feedback: dict[str, Any]
) -> float | None:
    eff_ratio = _effective_good_ratio(
        int(feedback.get("total") or 0), feedback.get("good_ratio")
    )
    return 1.0 - eff_ratio if eff_ratio is not None else None


class _Dimension(NamedTuple):
    """Single source of truth per dimension (OCP: add one entry to extend)."""

    key: HealthFactorKey
    weight: float
    budget_of: Callable[[float, float], float]
    """(max_empty_recall_pct, min_good_ratio) → error-budget share."""
    bad_rate_of: Callable[[dict[str, Any], dict[str, Any]], float | None]
    """(retrieval_summary, feedback_summary) → bad-event rate; None = no data."""


_DIMENSIONS: tuple[_Dimension, ...] = (
    _Dimension(
        "retrieval",
        0.3,
        lambda pct, _ratio: pct / 100.0,
        _empty_recall_bad_rate,
    ),
    _Dimension(
        "latency",
        0.3,
        lambda _pct, _ratio: SLOW_REQUEST_BUDGET,
        _slow_request_bad_rate,
    ),
    _Dimension(
        "satisfaction",
        0.4,
        lambda _pct, ratio: 1.0 - ratio,
        _satisfaction_bad_rate,
    ),
)


def compute_health_score(
    retrieval: dict[str, Any],
    feedback: dict[str, Any],
    *,
    max_empty_recall_pct: float = 15.0,
    min_good_ratio: float = 0.6,
) -> HealthScoreResult:
    """Composite score = weight-adjusted mean of per-dimension budget rest.

    Factors without samples (or without a definable budget) get ``score=None``
    and release their weight to the active factors proportionally; when no
    factor has data the composite score is ``None``.
    """
    scores: dict[HealthFactorKey, int | None] = {}
    for dim in _DIMENSIONS:
        budget = dim.budget_of(max_empty_recall_pct, min_good_ratio)
        bad_rate = dim.bad_rate_of(retrieval, feedback)
        scores[dim.key] = (
            dimension_score(bad_rate, budget) if bad_rate is not None else None
        )

    active_weight = sum(dim.weight for dim in _DIMENSIONS if scores[dim.key] is not None)
    factors: list[HealthFactor] = [
        {
            "key": dim.key,
            "score": scores[dim.key],
            "weight": (
                dim.weight / active_weight
                if active_weight > 0 and scores[dim.key] is not None
                else 0.0
            ),
        }
        for dim in _DIMENSIONS
    ]
    weighted = sum((f["score"] or 0) * f["weight"] for f in factors)
    score: int | None = (
        round(min(100.0, max(0.0, weighted))) if active_weight > 0 else None
    )
    return {"score": score, "factors": factors}


def evaluate_burn_rate_alerts(
    long_retrieval: dict[str, Any],
    long_feedback: dict[str, Any],
    short_retrieval: dict[str, Any],
    short_feedback: dict[str, Any],
    *,
    max_empty_recall_pct: float = 15.0,
    min_good_ratio: float = 0.6,
) -> list[dict[str, Any]]:
    """MWMB alert check: fast/slow budget burn confirmed by both windows.

    A dimension alerts only when its burn rate exceeds the tier threshold on
    the long window AND the trailing short window simultaneously — filtering
    transient spikes (workbook Ch.5 §6). Zero-budget dimensions are skipped.
    """
    alerts: list[dict[str, Any]] = []
    for dim in _DIMENSIONS:
        budget = dim.budget_of(max_empty_recall_pct, min_good_ratio)
        if budget <= 0:
            continue
        bad_long = dim.bad_rate_of(long_retrieval, long_feedback)
        bad_short = dim.bad_rate_of(short_retrieval, short_feedback)
        if bad_long is None or bad_short is None:
            continue
        r_long = bad_long / budget
        r_short = bad_short / budget
        if r_long >= FAST_BURN_RATE and r_short >= FAST_BURN_RATE:
            alerts.append(_burn_alert("critical", dim.key, "fast", r_long, FAST_BURN_RATE))
        elif r_long >= SLOW_BURN_RATE and r_short >= SLOW_BURN_RATE:
            alerts.append(_burn_alert("warning", dim.key, "slow", r_long, SLOW_BURN_RATE))
    return alerts


def _burn_alert(
    level: str, key: str, tier: str, burn_rate: float, threshold: float
) -> dict[str, Any]:
    return {
        "level": level,
        "code": f"{key}_burn_{tier}",
        "current": round(burn_rate, 1),
        "threshold": threshold,
    }


# ---------------------------------------------------------------------------
# Summary assembly (service-layer orchestration; routers stay thin)
# ---------------------------------------------------------------------------


async def build_quality_summary(
    user_id: str,
    window_hours: int,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    max_empty_recall_pct: float = 15.0,
    max_p95_latency_ms: int = 8000,
    min_good_ratio: float = 0.6,
) -> dict[str, Any]:
    """Full quality-summary payload: metrics + health score + merged alerts.

    Fetches the long-window aggregates plus (when a bounded anchor exists)
    the trailing short window for the MWMB burn-rate check. Threshold and
    burn-rate alerts are concatenated — threshold breach is the stable
    legacy contract, burn rate adds severity semantics.
    """
    from repository.monitoring import evaluate_alerts, feedback_summary, retrieval_summary

    retrieval = await retrieval_summary(
        user_id,
        window_hours,
        since=since,
        until=until,
        latency_slo_ms=max_p95_latency_ms,
    )
    feedback = await feedback_summary(user_id, window_hours, since=since, until=until)

    threshold_alerts = evaluate_alerts(
        retrieval,
        feedback,
        max_empty_recall_pct=max_empty_recall_pct,
        max_p95_latency_ms=max_p95_latency_ms,
        min_good_ratio=min_good_ratio,
    )
    health_score = compute_health_score(
        retrieval,
        feedback,
        max_empty_recall_pct=max_empty_recall_pct,
        min_good_ratio=min_good_ratio,
    )

    # MWMB burn-rate check needs a trailing sub-window of the long one;
    # all-time queries without explicit bounds skip it (no bounded anchor).
    burn_alerts: list[dict[str, Any]] = []
    short_bounds = short_window_bounds(window_hours, since, until)
    if short_bounds is not None:
        short_since, short_until = short_bounds
        short_retrieval = await retrieval_summary(
            user_id,
            window_hours,
            since=short_since,
            until=short_until,
            latency_slo_ms=max_p95_latency_ms,
        )
        short_feedback = await feedback_summary(
            user_id, window_hours, since=short_since, until=short_until
        )
        burn_alerts = evaluate_burn_rate_alerts(
            retrieval,
            feedback,
            short_retrieval,
            short_feedback,
            max_empty_recall_pct=max_empty_recall_pct,
            min_good_ratio=min_good_ratio,
        )

    return {
        "window_hours": window_hours,
        "retrieval": retrieval,
        "feedback": feedback,
        "health_score": health_score,
        "alerts": [*threshold_alerts, *burn_alerts],
    }
