"""Snapshot/restore lifecycle for process-global singletons shared by tests.

``core.infra.database`` keeps process-wide singletons (engine, session
factory, ...) and ``core.app_lifespan`` exposes ``init_db``. Several test
packages rebind these globals; every rebinding must pair with a restore or
state leaks into unrelated tests on the same xdist worker (symptoms appear
only under specific file orders — the classic flaky isolation bug).

This module is the SINGLE OWNER of that lifecycle:

- conftests temporarily rebind globals through :func:`patch_test_globals`;
- the root conftest installs an autouse guard that captures state before
  each test and restores it afterwards, catching any unmanaged mutation.

Unknown attribute names raise ``KeyError`` immediately, so a typo can never
silently create a brand-new module attribute.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

import core.app_lifespan as _lifespan_mod
import core.infra.database as _db_mod

#: Every ``core.infra.database`` global a test may legitimately rebind.
_DB_ATTRS: tuple[str, ...] = (
    "_async_engine",
    "_engine_loop",
    "_async_session_factory",
    "_factory_loop",
    "DATABASE_URL",
    "_LOOP_BOUND_DRIVER",
)

#: Every ``core.app_lifespan`` global a test may legitimately rebind.
_LIFESPAN_ATTRS: tuple[str, ...] = ("init_db",)


@dataclass(frozen=True)
class GlobalStateSnapshot:
    """Values of all tracked globals captured at one point in time."""

    db_attrs: dict[str, Any] = field(default_factory=dict)
    lifespan_attrs: dict[str, Any] = field(default_factory=dict)


def capture_global_state() -> GlobalStateSnapshot:
    """Read all tracked globals into an immutable snapshot."""
    return GlobalStateSnapshot(
        db_attrs={name: getattr(_db_mod, name) for name in _DB_ATTRS},
        lifespan_attrs={name: getattr(_lifespan_mod, name) for name in _LIFESPAN_ATTRS},
    )


def restore_global_state(snapshot: GlobalStateSnapshot) -> None:
    """Write a snapshot back, undoing every mutation made after it was taken."""
    for name, value in snapshot.db_attrs.items():
        setattr(_db_mod, name, value)
    for name, value in snapshot.lifespan_attrs.items():
        setattr(_lifespan_mod, name, value)


@contextlib.contextmanager
def patch_test_globals(
    *,
    db: Mapping[str, Any] | None = None,
    lifespan: Mapping[str, Any] | None = None,
) -> Iterator[None]:
    """Temporarily rebind tracked globals; always restores on exit.

    Usage::

        with patch_test_globals(db={"_async_session_factory": factory}):
            ...

    Restores the prior state even when the body raises, so an overwriting
    test can never poison later tests on the same worker.
    """
    unknown = set(db or {}) - set(_DB_ATTRS)
    unknown |= set(lifespan or {}) - set(_LIFESPAN_ATTRS)
    if unknown:
        msg = f"untracked global(s) {sorted(unknown)}; known: {_DB_ATTRS + _LIFESPAN_ATTRS}"
        raise KeyError(msg)

    snapshot = capture_global_state()
    for name, value in (db or {}).items():
        setattr(_db_mod, name, value)
    for name, value in (lifespan or {}).items():
        setattr(_lifespan_mod, name, value)
    try:
        yield
    finally:
        restore_global_state(snapshot)
