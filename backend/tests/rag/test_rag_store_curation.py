"""Tests for chunk curation mixin (rag/rag_store_curation.py)."""

import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rag.rag_store_curation import (
    CurationMixin,
    _hash_chunk_id,
    _vector_literal,
)


class _AsyncSessionCtx:
    def __init__(self, session: AsyncMock):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        pass


class _SessionFactory:
    def __init__(self, session: AsyncMock):
        self._session = session

    def __call__(self):
        return _AsyncSessionCtx(self._session)


class _TestableStore(CurationMixin):
    """Concrete subclass for testing — provides _ensure_table stub."""

    async def _ensure_table(self):
        pass


def _patch_db(session: AsyncMock):
    factory = _SessionFactory(session)
    return patch("core.infra.database.get_session_factory", return_value=factory)


# ── Pure functions ────────────────────────────────────────────────────


class TestVectorLiteral:
    def test_basic(self):
        assert _vector_literal([1.0, 2.0, 3.0]) == "[1.0,2.0,3.0]"

    def test_single(self):
        assert _vector_literal([0.5]) == "[0.5]"

    def test_empty(self):
        assert _vector_literal([]) == "[]"

    def test_negative_values(self):
        assert _vector_literal([-1.5, 0.0, 2.5]) == "[-1.5,0.0,2.5]"

    def test_many_dims(self):
        v = [0.1 * i for i in range(10)]
        result = _vector_literal(v)
        assert result.startswith("[")
        assert result.endswith("]")
        assert result.count(",") == 9


class TestHashChunkId:
    def test_no_salt(self):
        expected = hashlib.sha256(b"hello").hexdigest()[:16]
        assert _hash_chunk_id("hello") == expected

    def test_with_salt(self):
        expected = hashlib.sha256(b"salt:hello").hexdigest()[:16]
        assert _hash_chunk_id("hello", salt="salt") == expected

    def test_deterministic(self):
        assert _hash_chunk_id("x") == _hash_chunk_id("x")

    def test_different_text_different_hash(self):
        assert _hash_chunk_id("a") != _hash_chunk_id("b")

    def test_different_salt_different_hash(self):
        assert _hash_chunk_id("x", salt="s1") != _hash_chunk_id("x", salt="s2")

    def test_unicode(self):
        h = _hash_chunk_id("你好世界")
        assert len(h) == 16


# ── CurationMixin methods ────────────────────────────────────────────


class TestChunkOwnerOk:
    @pytest.mark.asyncio
    async def test_owner_exists(self):
        store = _TestableStore()
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        session.execute = AsyncMock(return_value=mock_result)

        result = await store._chunk_owner_ok(session, "c1", "a1", "u1")
        assert result is True
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_owner_not_exists(self):
        store = _TestableStore()
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await store._chunk_owner_ok(session, "c1", "a1", "u1")
        assert result is False


class TestUpdateChunkText:
    @pytest.mark.asyncio
    async def test_found_returns_new_id(self):
        store = _TestableStore()
        session = AsyncMock()
        owner_result = MagicMock()
        owner_result.scalar.return_value = 1
        update_result = MagicMock()
        call_count = 0

        async def _execute(sql_or_text, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return owner_result
            return update_result

        session.execute = AsyncMock(side_effect=_execute)
        session.commit = AsyncMock()

        with _patch_db(session):
            new_id = await store.update_chunk_text(
                "c1", "a1", "u1", "new text", [0.1, 0.2], "bge-m3"
            )

        assert new_id is not None
        assert len(new_id) == 16
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_not_found_returns_none(self):
        store = _TestableStore()
        session = AsyncMock()
        owner_result = MagicMock()
        owner_result.scalar.return_value = None
        session.execute = AsyncMock(return_value=owner_result)

        with _patch_db(session):
            result = await store.update_chunk_text(
                "c1", "a1", "u1", "new text", [0.1], None
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_embedding_format(self):
        store = _TestableStore()
        session = AsyncMock()
        owner_result = MagicMock()
        owner_result.scalar.return_value = 1
        update_result = MagicMock()
        call_count = 0

        async def _execute(sql_or_text, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return owner_result
            return update_result

        session.execute = AsyncMock(side_effect=_execute)
        session.commit = AsyncMock()

        with _patch_db(session):
            await store.update_chunk_text(
                "c1", "a1", "u1", "text", [1.0, 2.0, 3.0], "model"
            )

        update_call = session.execute.call_args_list[1]
        params = update_call[0][1]
        assert params["emb"] == "[1.0,2.0,3.0]"


class TestAddManualChunk:
    @pytest.mark.asyncio
    async def test_basic(self):
        store = _TestableStore()
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        with _patch_db(session):
            chunk_id = await store.add_manual_chunk(
                "a1", "u1", "hello", [0.1, 0.2], "bge-m3"
            )

        assert len(chunk_id) == 16
        session.commit.assert_awaited_once()
        insert_call = session.execute.call_args_list[0]
        params = insert_call[0][1]
        assert params["uid"] == "u1"
        assert params["aid"] == "a1"
        assert params["txt"] == "hello"

    @pytest.mark.asyncio
    async def test_with_asset_name(self):
        store = _TestableStore()
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        with _patch_db(session):
            await store.add_manual_chunk(
                "a1", "u1", "text", [0.1], "m", asset_name="doc.pdf"
            )

        insert_call = session.execute.call_args_list[0]
        meta = json.loads(insert_call[0][1]["meta"])
        assert meta["asset_name"] == "doc.pdf"

    @pytest.mark.asyncio
    async def test_without_asset_name(self):
        store = _TestableStore()
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        with _patch_db(session):
            await store.add_manual_chunk(
                "a1", "u1", "text", [0.1], "m", asset_name=None
            )

        insert_call = session.execute.call_args_list[0]
        meta = json.loads(insert_call[0][1]["meta"])
        assert "asset_name" not in meta

    @pytest.mark.asyncio
    async def test_with_extra_metadata(self):
        store = _TestableStore()
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        with _patch_db(session):
            await store.add_manual_chunk(
                "a1", "u1", "text", [0.1], "m",
                extra_metadata={"qa": True, "question": "what?"},
            )

        insert_call = session.execute.call_args_list[0]
        meta = json.loads(insert_call[0][1]["meta"])
        assert meta["qa"] is True
        assert meta["question"] == "what?"

    @pytest.mark.asyncio
    async def test_metadata_manual_flag(self):
        store = _TestableStore()
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        with _patch_db(session):
            await store.add_manual_chunk(
                "a1", "u1", "text", [0.1], "m"
            )

        insert_call = session.execute.call_args_list[0]
        meta = json.loads(insert_call[0][1]["meta"])
        assert meta["manual"] is True

    @pytest.mark.asyncio
    async def test_session_id_format(self):
        store = _TestableStore()
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        with _patch_db(session):
            await store.add_manual_chunk(
                "a1", "u1", "text", [0.1], "m"
            )

        insert_call = session.execute.call_args_list[0]
        params = insert_call[0][1]
        assert params["sid"] == "asset:a1"


class TestSetChunkEnabled:
    @pytest.mark.asyncio
    async def test_enable(self):
        store = _TestableStore()
        session = AsyncMock()
        owner_result = MagicMock()
        owner_result.scalar.return_value = 1
        update_result = MagicMock()
        call_count = 0

        async def _execute(sql_or_text, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return owner_result
            return update_result

        session.execute = AsyncMock(side_effect=_execute)
        session.commit = AsyncMock()

        with _patch_db(session):
            result = await store.set_chunk_enabled("c1", "a1", "u1", True)

        assert result is True
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disable(self):
        store = _TestableStore()
        session = AsyncMock()
        owner_result = MagicMock()
        owner_result.scalar.return_value = 1
        update_result = MagicMock()
        call_count = 0

        async def _execute(sql_or_text, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return owner_result
            return update_result

        session.execute = AsyncMock(side_effect=_execute)
        session.commit = AsyncMock()

        with _patch_db(session):
            result = await store.set_chunk_enabled("c1", "a1", "u1", False)

        assert result is True

    @pytest.mark.asyncio
    async def test_not_found(self):
        store = _TestableStore()
        session = AsyncMock()
        owner_result = MagicMock()
        owner_result.scalar.return_value = None
        session.execute = AsyncMock(return_value=owner_result)

        with _patch_db(session):
            result = await store.set_chunk_enabled("c1", "a1", "u1", True)

        assert result is False


class TestDeleteChunk:
    @pytest.mark.asyncio
    async def test_found(self):
        store = _TestableStore()
        session = AsyncMock()
        owner_result = MagicMock()
        owner_result.scalar.return_value = 1
        delete_result = MagicMock()
        call_count = 0

        async def _execute(sql_or_text, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return owner_result
            return delete_result

        session.execute = AsyncMock(side_effect=_execute)
        session.commit = AsyncMock()

        with _patch_db(session):
            result = await store.delete_chunk("c1", "a1", "u1")

        assert result is True
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_not_found(self):
        store = _TestableStore()
        session = AsyncMock()
        owner_result = MagicMock()
        owner_result.scalar.return_value = None
        session.execute = AsyncMock(return_value=owner_result)

        with _patch_db(session):
            result = await store.delete_chunk("c1", "a1", "u1")

        assert result is False
