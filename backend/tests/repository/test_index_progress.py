"""Index progress repository tests — Redis mocked via broker.get_redis."""

from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.unit

from repository.index_progress import get_index_progress, set_index_progress


@pytest.fixture
def mock_redis():
    """可控的 Redis 桩：set/get 落到内存 dict，并记录写入参数。"""
    store: dict[str, str] = {}
    writes: list[tuple[str, str, dict]] = []

    async def _fake_set(key: str, value: str, **kwargs: object) -> bool:
        writes.append((key, value, kwargs))
        store[key] = value
        return True

    async def _fake_get(key: str) -> str | None:
        return store.get(key)

    redis = AsyncMock()
    redis.set.side_effect = _fake_set
    redis.get.side_effect = _fake_get
    with patch("repository.index_progress.get_redis", return_value=redis):
        yield store, writes


class TestIndexProgress:
    async def test_set_and_get_progress(self, mock_redis):
        """Should set and get index progress."""
        asset_id = "test_asset_123"

        await set_index_progress(
            asset_id=asset_id,
            stage="chunking",
            percentage=50,
            message="Processing chunks...",
        )

        progress = await get_index_progress(asset_id)
        assert progress is not None
        assert progress["stage"] == "chunking"
        assert progress["percentage"] == 50
        assert progress["message"] == "Processing chunks..."

    async def test_get_nonexistent_progress(self, mock_redis):
        """Should return None for nonexistent asset."""
        progress = await get_index_progress("nonexistent_asset")
        assert progress is None

    async def test_update_progress(self, mock_redis):
        """Should update progress for same asset."""
        asset_id = "test_asset_456"

        await set_index_progress(asset_id, "parsing", 10, "Starting...")
        await set_index_progress(asset_id, "chunking", 50, "Chunking...")
        await set_index_progress(asset_id, "embedding", 80, "Embedding...")

        progress = await get_index_progress(asset_id)
        assert progress is not None
        assert progress["stage"] == "embedding"
        assert progress["percentage"] == 80

    async def test_progress_stages(self, mock_redis):
        """Should handle all progress stages."""
        asset_id = "test_asset_stages"
        stages = ["parsing", "chunking", "embedding", "storing", "done"]

        for i, stage in enumerate(stages):
            percentage = (i + 1) * 20
            await set_index_progress(asset_id, stage, percentage, f"Stage: {stage}")

            progress = await get_index_progress(asset_id)
            assert progress is not None
            assert progress["stage"] == stage
            assert progress["percentage"] == percentage

    async def test_ttl_set_on_write(self, mock_redis):
        """写入必须带 TTL（10 分钟），否则进度键永不回收。"""
        from repository.index_progress import PROGRESS_TTL_SECONDS

        _store, writes = mock_redis
        asset_id = "test_asset_ttl"
        await set_index_progress(asset_id, "done", 100, "Done")
        assert writes[0][2]["ex"] == PROGRESS_TTL_SECONDS

    async def test_redis_failure_degrades_gracefully(self):
        """Redis 故障时 set/get 静默降级（不抛异常）。"""
        with patch("repository.index_progress.get_redis", side_effect=ConnectionError("down")):
            await set_index_progress("a1", "parsing", 10, "x")
            assert await get_index_progress("a1") is None
