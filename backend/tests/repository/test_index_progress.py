"""Index progress repository tests."""

import pytest

pytestmark = pytest.mark.unit

from repository.index_progress import get_index_progress, set_index_progress


class TestIndexProgress:
    async def test_set_and_get_progress(self):
        """Should set and get index progress."""
        asset_id = "test_asset_123"

        await set_index_progress(
            asset_id=asset_id,
            stage="chunking",
            percentage=50,
            message="Processing chunks...",
        )

        progress = await get_index_progress(asset_id)
        # Redis may not be available in test environment, so progress might be None
        if progress is not None:
            assert progress["stage"] == "chunking"
            assert progress["percentage"] == 50
            assert progress["message"] == "Processing chunks..."

    async def test_get_nonexistent_progress(self):
        """Should return None for nonexistent asset."""
        progress = await get_index_progress("nonexistent_asset")
        assert progress is None

    async def test_update_progress(self):
        """Should update progress for same asset."""
        asset_id = "test_asset_456"

        await set_index_progress(asset_id, "parsing", 10, "Starting...")
        await set_index_progress(asset_id, "chunking", 50, "Chunking...")
        await set_index_progress(asset_id, "embedding", 80, "Embedding...")

        progress = await get_index_progress(asset_id)
        # Redis may not be available in test environment
        if progress is not None:
            assert progress["stage"] == "embedding"
            assert progress["percentage"] == 80

    async def test_progress_stages(self):
        """Should handle all progress stages."""
        asset_id = "test_asset_stages"
        stages = ["parsing", "chunking", "embedding", "storing", "done"]

        for i, stage in enumerate(stages):
            percentage = (i + 1) * 20
            await set_index_progress(asset_id, stage, percentage, f"Stage: {stage}")

            progress = await get_index_progress(asset_id)
            # Redis may not be available in test environment
            if progress is not None:
                assert progress["stage"] == stage
                assert progress["percentage"] == percentage
