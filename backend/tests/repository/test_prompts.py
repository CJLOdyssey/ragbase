"""Repository tests for Prompt CRUD operations."""

import uuid

import pytest
from repository.prompts import (
    create_prompt,
    delete_prompt,
    get_prompts,
    update_prompt,
)


@pytest.mark.requirement("REQ-PROMPT-001")
@pytest.mark.asyncio
async def test_create_prompt(db_engine):
    """create_prompt persists a new PromptDB row and returns it with an ID."""
    prompt = await create_prompt(
        {
            "name": "test-prompt-repo",
            "category": "general",
            "content": "You are a helpful assistant.",
        }
    )
    assert prompt is not None
    assert prompt.id is not None
    assert prompt.name == "test-prompt-repo"
    assert prompt.category == "general"
    assert prompt.content == "You are a helpful assistant."
    assert prompt.status == "active"


@pytest.mark.requirement("REQ-PROMPT-001")
@pytest.mark.asyncio
async def test_list_prompts(db_engine):
    """get_prompts returns a list of PromptDB objects with expected attrs."""
    await create_prompt(
        {
            "name": f"prompt-{uuid.uuid4().hex[:6]}",
            "category": "system",
            "content": "System prompt content",
        }
    )
    prompts = await get_prompts()
    assert isinstance(prompts, list)
    assert len(prompts) >= 1
    first = prompts[0]
    assert first.id is not None
    assert first.name is not None
    assert first.content is not None
    assert first.category is not None


@pytest.mark.requirement("REQ-PROMPT-001")
@pytest.mark.asyncio
async def test_update_prompt_content(db_engine):
    """Updating a prompt's content persists and is reflected in a fresh read."""
    prompt = await create_prompt(
        {
            "name": "update-test",
            "category": "code",
            "content": "Original content.",
        }
    )
    updated = await update_prompt(prompt.id, {"content": "Modified content."})
    assert updated is not None
    assert updated.content == "Modified content."
    assert updated.version == "v1.0.1"
    updated2 = await update_prompt(prompt.id, {"content": "Another change."})
    assert updated2 is not None
    assert updated2.version == "v1.0.2"
    # Cross-check with list
    prompts = await get_prompts()
    found = [p for p in prompts if p.id == prompt.id]
    assert len(found) == 1
    assert found[0].content == "Another change."
    assert found[0].version == "v1.0.2"


@pytest.mark.requirement("REQ-PROMPT-001")
@pytest.mark.asyncio
async def test_delete_prompt(db_engine):
    """delete_prompt removes the row and returns True."""
    prompt = await create_prompt(
        {
            "name": "delete-test",
            "category": "general",
            "content": "To be deleted.",
        }
    )
    deleted = await delete_prompt(prompt.id)
    assert deleted is True
    prompts = await get_prompts()
    assert all(p.id != prompt.id for p in prompts)


@pytest.mark.asyncio
async def test_delete_prompt_not_found(db_engine):
    """Deleting a non-existent prompt returns False."""
    deleted = await delete_prompt(str(uuid.uuid4()))
    assert deleted is False


@pytest.mark.asyncio
async def test_update_prompt_name(db_engine):
    """Updating a prompt's name field works independently."""
    prompt = await create_prompt(
        {
            "name": "rename-me",
            "category": "general",
            "content": "Content.",
        }
    )
    updated = await update_prompt(prompt.id, {"name": "renamed"})
    assert updated is not None
    assert updated.name == "renamed"
    assert updated.content == "Content."
