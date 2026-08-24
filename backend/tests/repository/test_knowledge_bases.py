"""Knowledge bases router tests."""

import pytest

pytestmark = pytest.mark.unit

from repository.assets import create_asset, get_asset, set_asset_indexed
from repository.knowledge_bases import (
    assign_asset_to_kb,
    change_embed_model,
    change_indexing_config,
    create_kb,
    delete_kb,
    get_kb,
    list_kbs,
    update_kb,
)


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

    async def test_create_kb_with_embed_model(self):
        """Should persist the bound embedding model."""
        kb = await create_kb(
            user_id="test_user",
            name="测试知识库",
            description="",
            embed_model="bge-m3",
        )

        retrieved = await get_kb(kb.id, "test_user")
        assert retrieved is not None
        assert retrieved.embed_model == "bge-m3"

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


class TestChangeEmbedModel:
    async def test_rebind_resets_indexed_assets(self):
        """Model change should reset the KB's indexed assets and report them."""
        kb = await create_kb(
            user_id="test_user", name="库", description="", embed_model="bge-m3"
        )
        kept = await create_asset(
            user_id="test_user",
            name="a.pdf",
            asset_type="document",
            size_bytes=1,
            storage_path="/tmp/a.pdf",
        )
        other = await create_asset(
            user_id="test_user",
            name="b.pdf",
            asset_type="document",
            size_bytes=1,
            storage_path="/tmp/b.pdf",
        )
        for asset in (kept, other):
            await set_asset_indexed(asset.id, True)
        await assign_asset_to_kb(kept.id, kb.id, "test_user")

        updated, affected = await change_embed_model(
            kb.id, "test_user", "text-embedding-v3"
        )

        assert updated is not None
        assert updated.embed_model == "text-embedding-v3"
        assert affected == [kept.id]
        refreshed = await get_asset(kept.id)
        assert refreshed is not None and refreshed.indexed is False
        untouched = await get_asset(other.id)
        assert untouched is not None and untouched.indexed is True

    async def test_same_model_is_noop(self):
        """Rebinding to the identical model must not invalidate assets."""
        kb = await create_kb(
            user_id="test_user", name="库", description="", embed_model="bge-m3"
        )
        asset = await create_asset(
            user_id="test_user",
            name="a.pdf",
            asset_type="document",
            size_bytes=1,
            storage_path="/tmp/a.pdf",
        )
        await set_asset_indexed(asset.id, True)
        await assign_asset_to_kb(asset.id, kb.id, "test_user")

        updated, affected = await change_embed_model(kb.id, "test_user", "bge-m3")

        assert updated is not None
        assert affected == []
        refreshed = await get_asset(asset.id)
        assert refreshed is not None and refreshed.indexed is True

    async def test_wrong_user_returns_none(self):
        kb = await create_kb(
            user_id="test_user", name="库", description="", embed_model="bge-m3"
        )
        updated, affected = await change_embed_model(
            kb.id, "wrong_user", "text-embedding-v3"
        )
        assert updated is None
        assert affected == []


class TestChangeIndexingConfig:
    async def test_parser_config_change_invalidates_assets(self):
        """Chunking-param change must reset indexed assets like a model change."""
        kb = await create_kb(
            user_id="test_user",
            name="库",
            description="",
            embed_model="bge-m3",
            parser_config={"chunk_size": 512, "overlap": 64},
        )
        asset = await create_asset(
            user_id="test_user",
            name="a.pdf",
            asset_type="document",
            size_bytes=1,
            storage_path="/tmp/a.pdf",
        )
        await set_asset_indexed(asset.id, True)
        await assign_asset_to_kb(asset.id, kb.id, "test_user")

        updated, affected = await change_indexing_config(
            kb.id,
            "test_user",
            parser_config={"chunk_size": 256, "overlap": 32},
        )

        assert updated is not None
        assert updated.parser_config == {"chunk_size": 256, "overlap": 32}
        assert affected == [asset.id]
        refreshed = await get_asset(asset.id)
        assert refreshed is not None and refreshed.indexed is False

    async def test_same_parser_config_is_noop(self):
        cfg = {"chunk_size": 512, "overlap": 64}
        kb = await create_kb(
            user_id="test_user", name="库", description="", embed_model="bge-m3",
            parser_config=cfg,
        )
        asset = await create_asset(
            user_id="test_user",
            name="a.pdf",
            asset_type="document",
            size_bytes=1,
            storage_path="/tmp/a.pdf",
        )
        await set_asset_indexed(asset.id, True)
        await assign_asset_to_kb(asset.id, kb.id, "test_user")

        updated, affected = await change_indexing_config(
            kb.id, "test_user", parser_config=dict(cfg)
        )
        assert updated is not None and affected == []
