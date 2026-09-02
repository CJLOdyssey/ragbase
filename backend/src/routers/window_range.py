"""Shared time-range parsing/validation for monitoring + logs read endpoints.

Legacy callers pass ``window_hours`` (sliding window ending now). Custom
range callers pass ``since``/``until`` ISO datetimes, which override the
sliding-window lower bound. One place owns validation so every endpoint
behaves identically: future ``until`` rejected, inverted range rejected,
span capped at 90 days to keep aggregates bounded like ``window_hours``.
"""

from datetime import UTC, datetime, timedelta
from typing import NamedTuple

from fastapi import HTTPException, Query

_MAX_CUSTOM_SPAN = timedelta(days=90)
_FUTURE_TOLERANCE = timedelta(minutes=5)


class WindowBounds(NamedTuple):
    """Resolved bounds passed down to repository aggregations."""

    window_hours: int
    """Echoed legacy parameter; lower bound is ignored when ``since`` set."""
    since: datetime | None
    """Lower bound; None = unbounded past."""
    until: datetime | None
    """Upper bound; None = now."""


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def validate_since_until(
    since: datetime | None,
    until: datetime | None,
) -> tuple[datetime | None, datetime | None]:
    """Validate an absolute ``since``/``until`` pair and return aware values.

    Shared contract for monitoring and retrieval-logs range pickers:
      - ``until`` in the future (beyond a 5-minute tolerance) → rejected
      - ``since >= effective upper bound`` (inverted/empty range) → rejected
      - span longer than 90 days → rejected (keeps aggregates bounded)

    Raises ``HTTPException(422)`` on violation; returns ``(since, until)``
    with timezone-aware datetimes (naive input is assumed to be UTC).
    """
    if since is None and until is None:
        return None, None

    now = datetime.now(UTC)
    upper = _aware(until) if until is not None else None
    if upper is not None and upper > now + _FUTURE_TOLERANCE:
        raise HTTPException(status_code=422, detail="until 不能晚于当前时间")

    lower = _aware(since) if since is not None else None
    if lower is not None:
        effective_upper = upper or now
        if lower >= effective_upper:
            raise HTTPException(status_code=422, detail="since 必须早于 until")
        if effective_upper - lower > _MAX_CUSTOM_SPAN:
            raise HTTPException(
                status_code=422, detail="自定义时间范围不能超过 90 天"
            )

    return lower, upper


def bounded_window(
    window_hours: int = Query(24, ge=0, le=24 * 30),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
) -> WindowBounds:
    """FastAPI dependency resolving and validating the common time range."""
    lower, upper = validate_since_until(since, until)
    return WindowBounds(
        window_hours=window_hours, since=lower, until=upper
    )
