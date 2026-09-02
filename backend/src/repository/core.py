"""Shared repository helpers — owner filtering and pagination."""

from typing import Any, cast

from sqlalchemy import Select
from sqlalchemy.orm import DeclarativeBase


def apply_owner_filter(
    stmt: Select[Any],
    model_class: type[DeclarativeBase],
    owner_id: str | None = None,
) -> Select[Any]:
    """Append an ``owner_id`` filter to a select statement when RBAC is active.

    If ``owner_id`` is ``None`` or ``"*"``, no filtering is applied (admin view).

    Usage::

        stmt = apply_owner_filter(select(SessionDB), SessionDB, owner_id=user_id)
    """
    if owner_id and owner_id != "*" and hasattr(model_class, "owner_id"):
        return stmt.where(cast(Any, model_class).owner_id == owner_id)
    return stmt
