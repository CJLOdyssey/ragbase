"""Tests for versions.py repository."""

import uuid

import pytest

from core.infra.database import get_session_factory
from repository.versions import create_version, get_version, list_versions


class TestVersions:
    async def test_create_and_list_versions(self, db_engine):
        factory = get_session_factory()
        async with factory() as session:
            v1 = await create_version(
                session, "agent", "agent-1", {"name": "v1"}, "test"
            )
            assert v1["version_num"] == 1
            assert v1["resource_type"] == "agent"
            assert v1["resource_id"] == "agent-1"
            assert v1["created_by"] == "test"
            assert "created_at" in v1

            v2 = await create_version(
                session, "agent", "agent-1", {"name": "v2"}, "test"
            )
            assert v2["version_num"] == 2

    async def test_list_versions(self, db_engine):
        factory = get_session_factory()
        async with factory() as session:
            await create_version(session, "agent", "a1", {"k": "v1"}, "user1")
            await create_version(session, "agent", "a1", {"k": "v2"}, "user1")
            await create_version(session, "team", "t1", {"k": "v1"}, "user1")
            await session.commit()

        async with factory() as session:
            versions = await list_versions(session, "agent", "a1")
            assert len(versions) == 2
            # Newest first
            assert versions[0]["version_num"] == 2
            assert versions[1]["version_num"] == 1

    async def test_list_versions_with_pagination(self, db_engine):
        factory = get_session_factory()
        async with factory() as session:
            for i in range(5):
                await create_version(session, "agent", "a2", {"k": f"v{i}"}, "user1")
            await session.commit()

        async with factory() as session:
            versions = await list_versions(session, "agent", "a2", limit=2, offset=0)
            assert len(versions) == 2
            versions2 = await list_versions(session, "agent", "a2", limit=2, offset=2)
            assert len(versions2) == 2

    async def test_list_versions_empty(self, db_engine):
        factory = get_session_factory()
        async with factory() as session:
            versions = await list_versions(session, "agent", "nonexistent")
            assert versions == []

    async def test_get_version_found(self, db_engine):
        factory = get_session_factory()
        async with factory() as session:
            v = await create_version(session, "agent", "a1", {"x": 1}, "u1")
            await session.commit()
            found = await get_version(session, v["id"])
            assert found is not None
            assert found["id"] == v["id"]
            assert found["resource_type"] == "agent"
            assert found["snapshot"] == {"x": 1}

    async def test_get_version_not_found(self, db_engine):
        factory = get_session_factory()
        async with factory() as session:
            found = await get_version(session, str(uuid.uuid4()))
            assert found is None

    async def test_create_version_default_created_by(self, db_engine):
        factory = get_session_factory()
        async with factory() as session:
            v = await create_version(session, "agent", "a2", {"k": "v"})
            assert v["created_by"] is None

    async def test_list_versions_default_params(self, db_engine):
        factory = get_session_factory()
        async with factory() as session:
            for i in range(3):
                await create_version(session, "prompt", "p1", {"v": i}, "u")
            await session.commit()

        async with factory() as session:
            versions = await list_versions(session, "prompt", "p1")
            assert len(versions) == 3
