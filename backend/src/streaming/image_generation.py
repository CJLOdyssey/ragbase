"""Image generation via OpenAI-compatible /images/generations endpoints.

Used for image-capable models (model_types == "image", e.g. SiliconFlow
Kwai-Kolors/Kolors). The endpoint is non-streaming and returns a temporary
signed URL (typically valid ~1h).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_IMAGE_SIZE = "1024x1024"
REQUEST_TIMEOUT = httpx.Timeout(180.0, connect=15.0)


class ImageGenerationError(RuntimeError):
    """Raised when the image provider rejects or fails the generation request."""


async def generate_image(
    api_key: str,
    prompt: str,
    *,
    model: str,
    base_url: str | None = None,
    image_size: str = DEFAULT_IMAGE_SIZE,
    batch_size: int = 1,
) -> str:
    """Generate one image and return its URL.

    Args:
        api_key: Provider API key (Bearer).
        prompt: Text prompt describing the image.
        model: Image model id (e.g. "Kwai-Kolors/Kolors").
        base_url: Provider base URL; defaults to SiliconFlow.
        image_size: e.g. "1024x1024".
        batch_size: Number of images; only the first is returned.

    Raises:
        ImageGenerationError: On non-200 response or missing images in payload.
    """
    base = (base_url or "https://api.siliconflow.cn/v1").rstrip("/")
    url = f"{base}/images/generations"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "image_size": image_size,
        "batch_size": batch_size,
    }

    logger.info("Image generation request | model=%s | prompt=%d chars", model, len(prompt))
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, proxy=None) as client:
            response = await client.post(url, headers=headers, json=body)
    except httpx.HTTPError as exc:
        logger.error("Image generation transport error | url=%s", url, exc_info=True)
        raise ImageGenerationError(f"图片生成请求失败: {exc}") from exc

    if response.status_code != 200:
        detail = response.text[:500]
        logger.error("Image generation rejected | status=%d body=%s", response.status_code, detail)
        raise ImageGenerationError(f"图片生成被拒绝 (HTTP {response.status_code})")

    payload = response.json()
    images = payload.get("images") or []
    if not images:
        raise ImageGenerationError("图片生成返回为空")
    image_url = images[0].get("url")
    if not image_url:
        raise ImageGenerationError("图片生成返回缺少 URL")
    return str(image_url)
