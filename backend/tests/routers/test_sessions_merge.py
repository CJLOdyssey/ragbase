"""Session detail returns the full run tree — no folding, no versions array."""

import pytest


@pytest.mark.asyncio
async def test_merge_edit_chains_removed(db_engine):
    from services import session_service

    assert not hasattr(session_service, "merge_edit_chains")


@pytest.mark.asyncio
async def test_requirement_message_per_run(db_engine):
    from services.session_service import with_requirement_message

    run = type("R", (), {"id": "r1", "requirement": "q2", "created_at": None})()
    msgs = with_requirement_message(run, [])
    assert msgs[0]["id"] == "run-r1-requirement"
    assert msgs[0]["content"] == "q2"
    # 编辑链版本（requirement_versions）挂到合成消息 → 分支导航可用；
    # 无编辑历史时为 None（前端按 undefined/空处理）。
    assert msgs[0]["user_versions"] is None
