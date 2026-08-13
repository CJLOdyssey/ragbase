"""Tests for backend.core.infra.database — singleton engine and session factory."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import core.infra.database as db_mod
import pytest
from core.infra.database import (
    SLOW_QUERY_THRESHOLD,
    _attach_slow_query_listeners,
    get_async_engine,
    get_session_factory,
)


@pytest.fixture(autouse=True)
def _restore_database_globals():
    """Save and restore the global singletons so tests don't leak state."""
    saved_engine = db_mod._async_engine
    saved_factory = db_mod._async_session_factory
    saved_engine_loop = db_mod._engine_loop
    saved_factory_loop = db_mod._factory_loop
    yield
    db_mod._async_engine = saved_engine
    db_mod._async_session_factory = saved_factory
    db_mod._engine_loop = saved_engine_loop
    db_mod._factory_loop = saved_factory_loop


def test_slow_query_threshold_default() -> None:
    """SLOW_QUERY_THRESHOLD is 0.5 seconds."""
    assert SLOW_QUERY_THRESHOLD == 0.5


def test_attach_slow_query_listeners_accepts_any_engine() -> None:
    """_attach_slow_query_listeners works with any object that looks like an engine."""
    from sqlalchemy import create_engine

    real_engine = create_engine("sqlite://", echo=False)

    mock_engine = MagicMock()
    mock_engine.sync_engine = real_engine

    _attach_slow_query_listeners(mock_engine)

    # Listeners are attached (no exception = success)
    assert mock_engine.sync_engine is real_engine


@patch("core.infra.database.create_async_engine")
@patch("core.infra.database._attach_slow_query_listeners")
def test_get_async_engine_singleton(mock_attach: MagicMock, mock_create: MagicMock) -> None:
    """get_async_engine returns the same engine on repeated calls."""
    db_mod._async_engine = None
    db_mod._async_session_factory = None

    mock_engine = MagicMock()
    mock_create.return_value = mock_engine

    engine1 = get_async_engine()
    engine2 = get_async_engine()

    assert engine1 is engine2  # same singleton
    assert mock_create.call_count == 1  # created only once
    mock_attach.assert_called_once_with(mock_engine)


@patch("core.infra.database.create_async_engine")
@patch("core.infra.database._attach_slow_query_listeners")
def test_get_async_engine_with_zero_pool_size(mock_attach: MagicMock, mock_create: MagicMock) -> None:
    """When DATABASE_POOL_SIZE=0, poolclass should be NullPool."""
    db_mod._async_engine = None
    db_mod._async_session_factory = None

    mock_engine = MagicMock()
    mock_create.return_value = mock_engine

    with patch.dict("os.environ", {"DATABASE_POOL_SIZE": "0"}):
        engine = get_async_engine()

    assert engine is mock_engine
    # Check that create_async_engine was called with poolclass=NullPool
    kwargs = mock_create.call_args[1]
    from sqlalchemy.pool import NullPool

    assert kwargs.get("poolclass") is NullPool


@patch("core.infra.database.get_async_engine")
def test_get_session_factory(mock_get_engine: MagicMock) -> None:
    """get_session_factory returns a session factory bound to the engine."""
    db_mod._async_session_factory = None

    mock_engine = MagicMock()
    mock_get_engine.return_value = mock_engine

    factory = get_session_factory()
    assert factory is not None

    # Second call returns same factory
    factory2 = get_session_factory()
    assert factory2 is factory
    assert mock_get_engine.call_count == 1


@patch("core.infra.database.get_async_engine")
def test_get_async_engine_reuses_existing(mock_create: MagicMock) -> None:
    """If _async_engine is already set, get_async_engine returns it without creating new."""
    mock_engine = MagicMock()
    db_mod._async_engine = mock_engine

    engine = get_async_engine()
    assert engine is mock_engine
    mock_create.assert_not_called()


def test_get_async_engine_with_pool_kwargs() -> None:
    """get_async_engine passes pool_size and max_overflow when pool_size > 0."""
    db_mod._async_engine = None
    db_mod._async_session_factory = None

    mock_engine = MagicMock()
    env = {"DATABASE_POOL_SIZE": "5", "DATABASE_POOL_OVERFLOW": "3"}
    with patch("core.infra.database.create_async_engine", return_value=mock_engine) as mock_create, \
         patch("core.infra.database._attach_slow_query_listeners"), \
         patch.dict("os.environ", env, clear=False):
        engine = get_async_engine()

    assert engine is mock_engine
    _, kwargs = mock_create.call_args
    assert kwargs.get("pool_size") == 5
    assert kwargs.get("max_overflow") == 3


def test_re_exports_are_accessible() -> None:
    """All ORM models are re-exported from database module."""
    from core.infra.database import (
        AttachmentDB,
        ChatMessage,
        PromptDB,
        SessionDB,
        UserDB,
    )

    assert AttachmentDB is not None
    assert ChatMessage is not None
    assert PromptDB is not None
    assert SessionDB is not None
    assert UserDB is not None


def test_engine_recreated_across_loops(monkeypatch) -> None:
    """Celery threads pool runs each task under a fresh asyncio.run() loop; the
    engine must be recreated when the running loop changes (asyncpg would
    otherwise fail with "attached to a different loop")."""
    import asyncio

    # Test env uses sqlite (sync dialect — no loop binding); force the asyncpg
    # code path the fix targets.
    monkeypatch.setattr(db_mod, "_LOOP_BOUND_DRIVER", True)
    db_mod._async_engine = None
    db_mod._engine_loop = None

    engines: list[object] = []

    async def _get_engine() -> object:
        with patch("core.infra.database.create_async_engine") as mock_create, \
             patch("core.infra.database._attach_slow_query_listeners"):
            mock_create.return_value = MagicMock()
            engine = get_async_engine()
            engines.append(engine)
            return engine

    e1 = asyncio.run(_get_engine())
    e2 = asyncio.run(_get_engine())
    assert e1 is not e2  # different loops → different engines
    assert len(engines) == 2

    # Same loop still yields the singleton.
    async def _twice() -> tuple[object, object]:
        return get_async_engine(), get_async_engine()

    a, b = asyncio.run(_twice())
    assert a is b
