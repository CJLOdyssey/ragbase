"""Shared query helpers for monitoring repositories (public API).

These utilities are consumed by ``repository.monitoring``,
``repository.monitoring_timeseries`` and ``repository.latency_distribution``;
they are deliberately public (no leading underscore) because they cross
module boundaries within the repository package. Counts are aggregated in
SQL; latency percentiles are computed in Python from a bounded sample so
behavior stays identical between PostgreSQL and the in-memory sqlite used
by unit tests.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement
from sqlalchemy.orm import InstrumentedAttribute

# Cap latency samples pulled for percentile computation (defensive bound for
# very large windows — alerting percentiles stay stable beyond this).
LATENCY_SAMPLE_LIMIT = 10000


def window_since(window_hours: int) -> datetime | None:
    """Window lower bound; None means "all time" (window_hours <= 0)."""
    if window_hours <= 0:
        return None
    return datetime.now(UTC) - timedelta(hours=window_hours)


def resolve_window_lower(
    window_hours: int, since: datetime | None
) -> datetime | None:
    """Custom ``since`` overrides the sliding-window lower bound."""
    return since if since is not None else window_since(window_hours)


def window_conds(
    user_col: InstrumentedAttribute[Any],
    time_col: InstrumentedAttribute[datetime],
    user_id: str,
    lower: datetime | None,
    upper: datetime | None = None,
) -> list[ColumnElement[bool]]:
    """Common WHERE conditions: user isolation + optional time bounds."""
    conds: list[ColumnElement[bool]] = [user_col == user_id]
    if lower is not None:
        conds.append(time_col >= lower)
    if upper is not None:
        conds.append(time_col <= upper)
    return conds


def percentile_nearest_rank(values: list[int], pct: int) -> int | None:
    """Nearest-rank percentile; None when no samples."""
    if not values:
        return None
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round(pct / 100 * len(ordered)) - 1))
    return ordered[idx]
