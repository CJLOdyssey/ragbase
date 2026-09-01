"""Tests for feedback router — 真实 run + 具体契约断言。"""

import pytest
from fastapi.testclient import TestClient


async def _seed_run(requirement: str = "测试需求") -> str:
    """直插 admin-login 的 session + 挂靠 run，返回 run_id。"""
    from repository import create_run

    session_id = await _seed_session()
    return await create_run(requirement, session_id=session_id)


async def _seed_session() -> str:
    from uuid import uuid4

    from core.infra.database import get_session_factory
    from orm import SessionDB

    factory = get_session_factory()
    sid = str(uuid4())
    async with factory() as session:
        session.add(SessionDB(id=sid, user_id="admin-login", title="fb-session"))
        await session.commit()
    return sid


@pytest.mark.asyncio
async def test_submit_feedback_invalid_run_id(client: TestClient):
    """run 不存在 → 404（RUN_NOT_FOUND）。"""
    response = client.post(
        "/api/runs/nonexistent-run/feedback",
        json={"rating": "good", "comment": "Great!"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_submit_feedback_missing_rating(client: TestClient):
    """rating 缺失 → 422。"""
    response = client.post(
        "/api/runs/some-run/feedback",
        json={"comment": "Great!"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_feedback_invalid_rating(client: TestClient):
    """run 不存在时先 404；对真实 run 提交非法 rating → 400。"""
    missing = client.post(
        "/api/runs/some-run/feedback",
        json={"rating": "invalid", "comment": "Great!"},
    )
    assert missing.status_code == 404

    run_id = await _seed_run()
    response = client.post(
        f"/api/runs/{run_id}/feedback",
        json={"rating": "invalid", "comment": "Great!"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_submit_feedback_good_rating(client: TestClient):
    """真实 run + good → 201，返回包含 rating 的记录。"""
    run_id = await _seed_run()
    response = client.post(
        f"/api/runs/{run_id}/feedback",
        json={"rating": "good", "comment": "Great!"},
    )
    assert response.status_code == 201
    assert response.json()["rating"] == "good"


@pytest.mark.asyncio
async def test_submit_feedback_bad_rating(client: TestClient):
    """真实 run + bad → 201，可在 /api/feedback 列表查回。"""
    run_id = await _seed_run()
    response = client.post(
        f"/api/runs/{run_id}/feedback",
        json={"rating": "bad", "comment": "Needs improvement"},
    )
    assert response.status_code == 201
    assert response.json()["rating"] == "bad"

    mine = client.get("/api/feedback")
    assert mine.status_code == 200
    assert any(f["rating"] == "bad" for f in mine.json())
