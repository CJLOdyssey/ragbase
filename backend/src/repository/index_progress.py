"""Index progress tracking — Redis-backed progress store for asset indexing."""

import json
from typing import Any

from core.infra.logging_config import get_logger

logger = get_logger(__name__)

PROGRESS_KEY_PREFIX = "index_progress:"
PROGRESS_TTL_SECONDS = 600  # 10 minutes


async def set_index_progress(
    asset_id: str, stage: str, percentage: int, message: str
) -> None:
    """Store indexing progress in Redis with a 10-minute TTL.

    Args:
        asset_id: The asset being indexed.
        stage: One of parsing, chunking, embedding, storing, done, failed.
        percentage: 0-100 progress percentage.
        message: Human-readable status message.
    """
    try:
        from broker import get_redis

        r = get_redis()
        key = f"{PROGRESS_KEY_PREFIX}{asset_id}"
        value = json.dumps(
            {"stage": stage, "percentage": percentage, "message": message},
            ensure_ascii=False,
        )
        await r.set(key, value, ex=PROGRESS_TTL_SECONDS)
    except Exception:
        logger.debug("set_index_progress failed for %s", asset_id, exc_info=True)


async def get_index_progress(asset_id: str) -> dict[str, Any] | None:
    """Retrieve indexing progress from Redis.

    Returns:
        Dict with stage, percentage, message — or None if no progress data.
    """
    try:
        from broker import get_redis

        r = get_redis()
        key = f"{PROGRESS_KEY_PREFIX}{asset_id}"
        raw = await r.get(key)
        if raw is None:
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        logger.debug("get_index_progress failed for %s", asset_id, exc_info=True)
        return None
