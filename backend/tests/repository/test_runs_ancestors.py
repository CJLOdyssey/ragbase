"""get_run_ancestors walks the parent_run_id chain to the root."""

import os

import pytest

os.environ.setdefault("KEY_VAULT_SECRET", "0123456789abcdef0123456789abcdef")
os.environ["AUTH_MODE"] = "legacy"
os.environ["AUTH_ENABLED"] = "0"
os.environ["RATE_LIMIT"] = "9999"
os.environ["CHECKPOINTER_BACKEND"] = "memory"
os.environ["DATABASE_POOL_SIZE"] = "0"


@pytest.mark.asyncio
async def test_get_run_ancestors_walks_chain(db_engine):
    from repository import create_run, get_run_ancestors

    r1 = await create_run("q1")
    r2 = await create_run("q2", parent_run_id=r1)
    r3 = await create_run("q3", parent_run_id=r2)
    chain = await get_run_ancestors(r3)
    assert [r.id for r in chain] == [r1, r2, r3]


@pytest.mark.asyncio
async def test_get_run_ancestors_unknown_returns_empty(db_engine):
    from repository import get_run_ancestors

    assert await get_run_ancestors("no-such-run") == []
