"""Tests for base.py — generic CRUD repository patterns."""

import uuid

import pytest
from repository.prompts import PromptRepository


class TestBaseRepository:
    async def test_get_one_found(self, db_engine):
        prompt = await PromptRepository.create_one({
            "name": "test-prompt",
            "category": "general",
            "content": "Hello",
        })
        found = await PromptRepository.get_one(prompt.id)
        assert found is not None
        assert found.id == prompt.id
        assert found.name == "test-prompt"

    async def test_get_one_not_found(self, db_engine):
        found = await PromptRepository.get_one(str(uuid.uuid4()))
        assert found is None

    async def test_get_all(self, db_engine):
        await PromptRepository.create_one({
            "name": "p1", "category": "c", "content": "c1",
        })
        await PromptRepository.create_one({
            "name": "p2", "category": "c", "content": "c2",
        })
        items = await PromptRepository.get_all()
        assert len(items) >= 2

    async def test_get_all_as_dicts(self, db_engine):
        await PromptRepository.create_one({
            "name": "dict-test", "category": "c", "content": "d",
        })
        dicts = await PromptRepository.get_all_as_dicts()
        assert len(dicts) >= 1
        assert isinstance(dicts[0], dict)
        assert "name" in dicts[0]
        assert dicts[0]["name"] == "dict-test"

    async def test_create_one(self, db_engine):
        obj = await PromptRepository.create_one({
            "name": "new-prompt",
            "category": "code",
            "content": "Write good code.",
        })
        assert obj.id is not None
        assert obj.name == "new-prompt"

    async def test_update_one(self, db_engine):
        obj = await PromptRepository.create_one({
            "name": "to-update",
            "category": "c",
            "content": "old",
        })
        updated = await PromptRepository.update_one(obj.id, {"content": "new", "name": None})
        assert updated is not None
        assert updated.content == "new"
        # name should NOT be updated since None was passed
        assert updated.name == "to-update"

    async def test_update_one_not_found(self, db_engine):
        result = await PromptRepository.update_one(str(uuid.uuid4()), {"name": "x"})
        assert result is None

    async def test_delete_one(self, db_engine):
        obj = await PromptRepository.create_one({
            "name": "to-delete", "category": "c", "content": "d",
        })
        deleted = await PromptRepository.delete_one(obj.id)
        assert deleted is True
        found = await PromptRepository.get_one(obj.id)
        assert found is None

    async def test_delete_one_not_found(self, db_engine):
        deleted = await PromptRepository.delete_one(str(uuid.uuid4()))
        assert deleted is False

    def test_to_dict_not_implemented(self):
        """BaseRepository.to_dict raises NotImplementedError."""
        from repository.base import BaseRepository
        with pytest.raises(NotImplementedError):
            BaseRepository.to_dict(None)
