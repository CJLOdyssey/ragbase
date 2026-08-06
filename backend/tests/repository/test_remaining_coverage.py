"""Tests for remaining uncovered repository code: attachments, memory, auth, tools, mcps, skills, keys_connectivity."""

import os
import unittest.mock
import uuid

os.environ.setdefault("KEY_VAULT_SECRET", "0123456789abcdef0123456789abcdef")
os.environ.setdefault("AUTH_MODE", "legacy")
os.environ.setdefault("AUTH_ENABLED", "0")
os.environ.setdefault("CHECKPOINTER_BACKEND", "memory")
os.environ.setdefault("DATABASE_POOL_SIZE", "0")


# ── Attachments ──────────────────────────────────────────────────────────


class TestAttachments:
    async def test_create_attachment(self, db_engine):
        from repository.attachments import create_attachment, get_attachment_by_id
        from repository.session_repo import create_session

        sess = await create_session(title="Att Test")
        att = await create_attachment(
            attachment_id=str(uuid.uuid4()),
            session_id=sess.id,
            filename="test.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            storage_path="/uploads/test.pdf",
        )
        assert att.id is not None
        assert att.filename == "test.pdf"
        assert att.storage_path == "/uploads/test.pdf"

        fetched = await get_attachment_by_id(att.id)
        assert fetched is not None
        assert fetched.filename == "test.pdf"

    async def test_create_attachment_with_optional_fields(self, db_engine):
        from repository.attachments import create_attachment
        from repository.session_repo import create_session

        sess = await create_session(title="Att Opt")
        att = await create_attachment(
            attachment_id=str(uuid.uuid4()),
            session_id=sess.id,
            filename="doc.txt",
            content_type="text/plain",
            size_bytes=100,
            storage_path="/tmp/doc.txt",
            run_id=str(uuid.uuid4()),
            extracted_text="Hello world",
        )
        assert att.run_id is not None
        assert att.extracted_text == "Hello world"

    async def test_get_attachment_not_found(self, db_engine):
        from repository.attachments import get_attachment_by_id
        result = await get_attachment_by_id("nonexistent")
        assert result is None

    async def test_list_attachments_by_session(self, db_engine):
        from repository.attachments import create_attachment, list_attachments_by_session
        from repository.session_repo import create_session

        sess = await create_session(title="List Att")
        for i in range(3):
            await create_attachment(
                attachment_id=str(uuid.uuid4()),
                session_id=sess.id,
                filename=f"file{i}.txt",
                content_type="text/plain",
                size_bytes=10 * (i + 1),
                storage_path=f"/tmp/file{i}.txt",
            )
        atts = await list_attachments_by_session(sess.id)
        assert len(atts) == 3

    async def test_list_attachments_empty(self, db_engine):
        from repository.attachments import list_attachments_by_session
        result = await list_attachments_by_session("nonexistent")
        assert result == []

    async def test_delete_attachment(self, db_engine):
        from repository.attachments import create_attachment, delete_attachment, get_attachment_by_id
        from repository.session_repo import create_session

        sess = await create_session(title="Del Att")
        att = await create_attachment(
            attachment_id=str(uuid.uuid4()),
            session_id=sess.id,
            filename="del.txt",
            content_type="text/plain",
            size_bytes=10,
            storage_path="/tmp/del.txt",
        )
        path = await delete_attachment(att.id)
        assert path == "/tmp/del.txt"
        assert await get_attachment_by_id(att.id) is None

    async def test_delete_attachment_not_found(self, db_engine):
        from repository.attachments import delete_attachment
        result = await delete_attachment("nonexistent")
        assert result is None


# ── Memory Repo ──────────────────────────────────────────────────────────


class TestMemoryRepo:
    async def test_create_memory_entry(self, db_engine):
        from repository.memory_repo import create_memory_entry
        from repository.session_repo import create_session

        sess = await create_session(title="Mem")
        mem = await create_memory_entry(
            session_id=sess.id,
            run_id=str(uuid.uuid4()),
            agent_role="developer",
            content_type="decision",
            summary="Use FastAPI",
            details="Chose FastAPI over Flask",
        )
        assert mem.id is not None
        assert mem.summary == "Use FastAPI"
        assert mem.agent_role == "developer"
        assert mem.details == "Chose FastAPI over Flask"

    async def test_create_memory_entry_default_details(self, db_engine):
        from repository.memory_repo import create_memory_entry
        from repository.session_repo import create_session

        sess = await create_session(title="Mem Def")
        mem = await create_memory_entry(
            session_id=sess.id,
            run_id=str(uuid.uuid4()),
            agent_role="pm",
            content_type="context",
            summary="Sprint planning done",
        )
        assert mem.details == ""

    async def test_get_session_memories(self, db_engine):
        from repository.memory_repo import create_memory_entry, get_session_memories
        from repository.session_repo import create_session

        sess = await create_session(title="Mem Get")
        await create_memory_entry(
            session_id=sess.id, run_id=str(uuid.uuid4()),
            agent_role="dev", content_type="decision", summary="First",
        )
        await create_memory_entry(
            session_id=sess.id, run_id=str(uuid.uuid4()),
            agent_role="dev", content_type="decision", summary="Second",
        )
        memories = await get_session_memories(sess.id)
        assert len(memories) == 2

    async def test_get_session_memories_empty(self, db_engine):
        from repository.memory_repo import get_session_memories
        result = await get_session_memories("nonexistent")
        assert result == []

    async def test_clear_session_memories(self, db_engine):
        from repository.memory_repo import (
            clear_session_memories,
            create_memory_entry,
            get_session_memories,
        )
        from repository.session_repo import create_session

        sess = await create_session(title="Mem Clear")
        for i in range(3):
            await create_memory_entry(
                session_id=sess.id, run_id=str(uuid.uuid4()),
                agent_role="dev", content_type="bug", summary=f"Bug {i}",
            )
        await clear_session_memories(sess.id)
        memories = await get_session_memories(sess.id)
        assert len(memories) == 0

    async def test_delete_memory_entry(self, db_engine):
        from repository.memory_repo import (
            create_memory_entry,
            delete_memory_entry,
            get_session_memories,
        )
        from repository.session_repo import create_session

        sess = await create_session(title="Mem Del")
        mem = await create_memory_entry(
            session_id=sess.id, run_id=str(uuid.uuid4()),
            agent_role="dev", content_type="decision", summary="To Delete",
        )
        result = await delete_memory_entry(mem.id)
        assert result is True
        memories = await get_session_memories(sess.id)
        assert len(memories) == 0

    async def test_delete_memory_entry_not_found(self, db_engine):
        from repository.memory_repo import delete_memory_entry
        result = await delete_memory_entry("nonexistent")
        assert result is False


# ── Auth: revoke_token_family ────────────────────────────────────────────


class TestAuthRevokeTokenFamily:
    async def test_revoke_token_family(self, db_engine):
        from core.seed import seed_default_roles_and_admin
        await seed_default_roles_and_admin()

        from repository.auth import (
            create_refresh_token,
            create_user,
            revoke_token_family,
        )
        user = await create_user("family@example.com", "hash")
        token, _ = await create_refresh_token(user.id)
        from repository.auth import consume_refresh_token
        consumed_user, family_id = await consume_refresh_token(token)
        assert consumed_user is not None

        # Create a new token in the same family
        token2, _ = await create_refresh_token(user.id, family_id=family_id)
        await revoke_token_family(family_id)

        # Token should now be consumed (revoked)
        consumed2, _ = await consume_refresh_token(token2)
        assert consumed2 is None


# ── Tools/MCPs/Skills: to_dict and list_tool_plugins ────────────────────


class TestKeysConnectivityV1Slash:
    def test_base_url_v1_trailing_slash(self):
        from repository.keys_connectivity import _test_connection_sync

        with unittest.mock.patch("urllib.request.urlopen") as mock_open:
            mock_resp = unittest.mock.MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = b'{"data": [{"id": "m1"}]}'
            mock_resp.__enter__ = unittest.mock.MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = unittest.mock.MagicMock(return_value=False)
            mock_open.return_value = mock_resp

            result = _test_connection_sync({
                "api_key": "sk-test",
                "provider": "openai",
                "base_url": "https://api.example.com/v1/",
            })
            assert result["success"] is True
            call_url = mock_open.call_args[0][0].full_url
            assert call_url.endswith("/models")

    def test_deepseek_provider_no_base_url(self):
        from repository.keys_connectivity import _test_connection_sync

        with unittest.mock.patch("urllib.request.urlopen") as mock_open:
            mock_resp = unittest.mock.MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = b'{"data": []}'
            mock_resp.__enter__ = unittest.mock.MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = unittest.mock.MagicMock(return_value=False)
            mock_open.return_value = mock_resp

            result = _test_connection_sync({
                "api_key": "sk-test",
                "provider": "deepseek",
                "base_url": "",
            })
            assert result["success"] is True
            call_url = mock_open.call_args[0][0].full_url
            assert "deepseek" in call_url

    def test_anthropic_provider_no_base_url(self):
        from repository.keys_connectivity import _test_connection_sync

        with unittest.mock.patch("urllib.request.urlopen") as mock_open:
            mock_resp = unittest.mock.MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = b'{"data": []}'
            mock_resp.__enter__ = unittest.mock.MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = unittest.mock.MagicMock(return_value=False)
            mock_open.return_value = mock_resp

            result = _test_connection_sync({
                "api_key": "sk-test",
                "provider": "anthropic",
                "base_url": "",
            })
            assert result["success"] is True
            call_url = mock_open.call_args[0][0].full_url
            assert "anthropic" in call_url
