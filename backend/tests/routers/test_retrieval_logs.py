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


@pytest.mark.asyncio
async def test_stats_hit_rate_not_degenerate_under_empty_only(client: TestClient):
    """Hit rate must stay baseline-scoped: empty-only filter must not pin it at 100%."""
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

    response = client.get("/api/retrieval-logs/stats?empty_only=true")
    assert response.status_code == 200
    hit_rate = response.json()["hitRate"]
    # Baseline scope: both rows counted, real ratio — not the filtered tautology.
    assert hit_rate["total"] == 2
    assert hit_rate["emptyRecall"] == 1
    assert hit_rate["hitRecall"] == 1
    assert hit_rate["emptyRecallRate"] == 50.0


@pytest.mark.asyncio
async def test_stats_latency_distribution_full_under_max_latency(client: TestClient):
    """Latency distribution must keep all buckets when max-latency filter hides slow rows."""
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

    response = client.get("/api/retrieval-logs/stats?max_latency_ms=100")
    assert response.status_code == 200
    data = response.json()
    # Baseline scope: >300ms bucket survives even though no row matches the filter.
    slow_bucket = next(
        b for b in data["latencyDistribution"] if b["range"] == ">300ms"
    )
    assert slow_bucket["count"] == 1
    assert data["hitRate"]["total"] == 2


@pytest.mark.asyncio
async def test_stats_trend_daily_subset_scope_under_empty_only(client: TestClient):
    """Volume trend / daily activity follow the filters (subset scope)."""
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

    response = client.get("/api/retrieval-logs/stats?empty_only=true")
    assert response.status_code == 200
    data = response.json()
    # Subset scope: only the empty-recall row appears in timing aggregates.
    assert sum(p["count"] for p in data["volumeTrend"]) == 1
    assert sum(d["count"] for d in data["dailyActivity"]) == 1
