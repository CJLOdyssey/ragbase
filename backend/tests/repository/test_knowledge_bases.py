"""Knowledge bases router tests."""

import pytest

pytestmark = pytest.mark.unit

from repository.knowledge_bases import create_kb, delete_kb, get_kb, list_kbs, update_kb


class TestKnowledgeBaseRepository:
    async def test_create_kb(self):
        """Should create a knowledge base."""
        kb = await create_kb(
            user_id="test_user",
            name="测试知识库",
            description="这是一个测试知识库",
        )

        assert kb.id is not None
        assert kb.user_id == "test_user"
        assert kb.name == "测试知识库"
        assert kb.description == "这是一个测试知识库"

    async def test_get_kb(self):
        """Should get a knowledge base by id."""
        kb = await create_kb(
            user_id="test_user",
            name="测试知识库",
            description="描述",
        )

        retrieved = await get_kb(kb.id, "test_user")
        assert retrieved is not None
        assert retrieved.id == kb.id
        assert retrieved.name == "测试知识库"

    async def test_get_kb_wrong_user(self):
        """Should return None when user doesn't match."""
        kb = await create_kb(
            user_id="test_user",
            name="测试知识库",
            description="描述",
        )

        retrieved = await get_kb(kb.id, "wrong_user")
        assert retrieved is None

    async def test_list_kbs(self):
        """Should list knowledge bases for user."""
        await create_kb(user_id="test_user", name="知识库1", description="")
        await create_kb(user_id="test_user", name="知识库2", description="")
        await create_kb(user_id="other_user", name="其他知识库", description="")

        kbs = await list_kbs("test_user")
        assert len(kbs) == 2
        assert all(kb.user_id == "test_user" for kb in kbs)

    async def test_update_kb(self):
        """Should update knowledge base."""
        kb = await create_kb(
            user_id="test_user",
            name="原始名称",
            description="原始描述",
        )

        updated = await update_kb(
            kb.id,
            "test_user",
            name="新名称",
            description="新描述",
        )

        assert updated is not None
        assert updated.name == "新名称"
        assert updated.description == "新描述"

    async def test_update_kb_partial(self):
        """Should update only provided fields."""
        kb = await create_kb(
            user_id="test_user",
            name="原始名称",
            description="原始描述",
        )

        updated = await update_kb(kb.id, "test_user", name="新名称")

        assert updated is not None
        assert updated.name == "新名称"
        assert updated.description == "原始描述"

    async def test_delete_kb(self):
        """Should delete knowledge base."""
        kb = await create_kb(
            user_id="test_user",
            name="测试知识库",
            description="描述",
        )

        result = await delete_kb(kb.id, "test_user")
        assert result is True

        retrieved = await get_kb(kb.id, "test_user")
        assert retrieved is None

    async def test_delete_kb_wrong_user(self):
        """Should return False when user doesn't match."""
        kb = await create_kb(
            user_id="test_user",
            name="测试知识库",
            description="描述",
        )

        result = await delete_kb(kb.id, "wrong_user")
        assert result is False

        # Should still exist
        retrieved = await get_kb(kb.id, "test_user")
        assert retrieved is not None
