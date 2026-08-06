"""Tests for backend.core.infra.database — singleton engine and session factory."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import core.infra.database as db_mod
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
    yield
    db_mod._async_engine = saved_engine
    db_mod._async_session_factory = saved_factory


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
        AgentConfigDB,
        AttachmentDB,
        ChatMessage,
        PromptDB,
        SessionDB,
        TeamDB,
        UserDB,
    )

    assert AgentConfigDB is not None
    assert AttachmentDB is not None
    assert ChatMessage is not None
    assert PromptDB is not None
    assert SessionDB is not None
    assert TeamDB is not None
    assert UserDB is not None
