"""Tests for retrieval_logs router."""

import pytest
from fastapi.testclient import TestClient
from repository.retrieval_logs import create_retrieval_log


@pytest.mark.asyncio
async def test_get_retrieval_logs_empty(client: TestClient):
    """Should return empty list when no logs exist."""
    response = client.get("/api/retrieval-logs")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_retrieval_logs_with_data(client: TestClient):
    """Should return logs for current user."""
    # Create some logs
    await create_retrieval_log(
        user_id="admin-login",
        query="测试查询1",
        latency_ms=100,
        hit_count=2,
    )
    await create_retrieval_log(
        user_id="admin-login",
        query="测试查询2",
        latency_ms=200,
        hit_count=1,
    )

    response = client.get("/api/retrieval-logs")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_get_retrieval_logs_pagination(client: TestClient):
    """Should support pagination."""
    # Create 5 logs
    for i in range(5):
        await create_retrieval_log(
            user_id="admin-login",
            query=f"查询{i}",
            latency_ms=100 + i * 10,
            hit_count=i,
        )

    # Get page 1
    response = client.get("/api/retrieval-logs?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2

    # Get page 2
    response = client.get("/api/retrieval-logs?page=2&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_get_retrieval_logs_filter_empty_only(client: TestClient):
    """Should filter logs with zero hits."""
    await create_retrieval_log(
        user_id="admin-login",
        query="有结果",
        latency_ms=100,
        hit_count=2,
    )
    await create_retrieval_log(
        user_id="admin-login",
        query="无结果",
        latency_ms=50,
        hit_count=0,
    )

    response = client.get("/api/retrieval-logs?empty_only=true")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["hitCount"] == 0


@pytest.mark.asyncio
async def test_get_retrieval_logs_filter_min_hit_count(client: TestClient):
    """Should filter logs by minimum hit count."""
    await create_retrieval_log(
        user_id="admin-login",
        query="查询1",
        latency_ms=100,
        hit_count=1,
    )
    await create_retrieval_log(
        user_id="admin-login",
        query="查询2",
        latency_ms=100,
        hit_count=3,
    )

    response = client.get("/api/retrieval-logs?min_hit_count=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["hitCount"] == 3


@pytest.mark.asyncio
async def test_get_retrieval_logs_filter_max_latency(client: TestClient):
    """Should filter logs by maximum latency."""
    await create_retrieval_log(
        user_id="admin-login",
        query="快速查询",
        latency_ms=50,
        hit_count=1,
    )
    await create_retrieval_log(
        user_id="admin-login",
        query="慢查询",
        latency_ms=500,
        hit_count=1,
    )

    response = client.get("/api/retrieval-logs?max_latency_ms=100")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["latencyMs"] == 50
