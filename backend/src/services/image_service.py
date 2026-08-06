"""ImageService — text-to-image via openai / dashscope / stability.

多源参照 2026-08-06:
  - openai:  POST {base}/images/generations → data[0].b64_json
  - dashscope: POST /api/v1/services/aigc/text2image/image-synthesis
              (X-DashScope-Async: enable) → task_id 轮询 → output.results[].url
  - stability: POST /v2beta/stable-image/generate/{sd3|core|ultra} → 二进制
"""

from __future__ import annotations

import asyncio
import base64
import os
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path

import httpx
from core.infra.logging_config import get_logger
from pydantic import BaseModel
from repository import get_api_key_for_use, get_default_api_key, get_run_for_user
from repository.attachments import create_attachment

logger = get_logger(__name__)

IMAGE_DIR = Path(os.environ.get("UPLOAD_DIR", "./uploads")) / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

_DASHSCOPE_IMAGE_API = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
_DASHSCOPE_TASK_API = "https://dashscope.aliyuncs.com/api/v1/tasks"
_STABILITY_API = "https://api.stability.ai/v2beta/stable-image/generate"

_MAX_POLL_ATTEMPTS = 60
_POLL_INTERVAL_S = 3.0


class ImageResult(BaseModel):
    attachment_id: str
    storage_path: str


def _new_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=15.0))


class ImageService:
    """Dispatch text-to-image calls to configured providers and persist results."""

    async def generate(
        self,
        run_id: str,
        prompt: str,
        provider: str,
        key_id: str | None = None,
        user_id: str = "",
    ) -> ImageResult:
        run = await get_run_for_user(run_id, user_id)
        if run is None:
            raise ValueError("run 不存在")
        assert run.session_id is not None  # get_run_for_user denies sessionless runs
        handler = _PROVIDER_HANDLERS.get(provider)
        if handler is None:
            raise ValueError(f"不支持的图像 provider: {provider}")
        api_key, base_url = await self._resolve_key(provider, key_id, user_id)
        png_bytes = await handler(self, api_key, base_url, prompt)

        filename = f"{run_id}-{uuid.uuid4().hex[:8]}.png"
        storage_path = str(IMAGE_DIR / filename)
        Path(storage_path).write_bytes(png_bytes)

        try:
            attachment = await create_attachment(
                attachment_id=str(uuid.uuid4()),
                session_id=run.session_id,
                filename=filename,
                content_type="image/png",
                size_bytes=len(png_bytes),
                storage_path=storage_path,
                run_id=run_id,
            )
        except Exception:
            Path(storage_path).unlink(missing_ok=True)
            raise
        logger.info("Image generated | run=%s | provider=%s | %s", run_id, provider, storage_path)
        return ImageResult(attachment_id=attachment.id, storage_path=storage_path)

    async def _resolve_key(
        self, provider: str, key_id: str | None, user_id: str
    ) -> tuple[str, str]:
        api_key: str | None = None
        base_url: str | None = None
        if key_id:
            entry = await get_api_key_for_use(key_id, user_id)
            if entry is None:
                raise ValueError("指定 API Key 不存在")
            api_key = entry.get("api_key")
            base_url = entry.get("base_url")
        if not api_key:
            entry = await get_default_api_key(user_id)
            if entry:
                api_key = entry["api_key"]
                base_url = entry.get("base_url")
        if not api_key:
            raise ValueError("请先在设置中配置 API Key")
        return api_key, base_url or _DEFAULT_BASE_URLS.get(provider, "")

    async def _openai(self, api_key: str, base_url: str, prompt: str, size: str = "1024x1024") -> bytes:
        url = f"{(base_url or 'https://api.openai.com/v1').rstrip('/')}/images/generations"
        async with _new_client() as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": "gpt-image-1", "prompt": prompt, "n": 1, "size": size},
            )
            resp.raise_for_status()
            data = resp.json()["data"][0]
            if data.get("b64_json"):
                return base64.b64decode(data["b64_json"])
            image_url = data.get("url")
            if not image_url:
                raise ValueError("openai images 响应缺少 b64_json/url")
            img_resp = await client.get(image_url)
            img_resp.raise_for_status()
            return img_resp.content

    async def _dashscope(self, api_key: str, base_url: str, prompt: str, size: str = "1024*1024") -> bytes:
        async with _new_client() as client:
            submit = await client.post(
                _DASHSCOPE_IMAGE_API,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "X-DashScope-Async": "enable",
                },
                json={
                    "model": "wanx2.1-t2i-turbo",
                    "input": {"prompt": prompt},
                    "parameters": {"size": size, "n": 1},
                },
            )
            submit.raise_for_status()
            task_id = submit.json()["output"]["task_id"]

            for _ in range(_MAX_POLL_ATTEMPTS):
                poll = await client.get(
                    f"{_DASHSCOPE_TASK_API}/{task_id}",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                poll.raise_for_status()
                output = poll.json()["output"]
                status = output["task_status"]
                if status == "SUCCEEDED":
                    image_url = (output.get("results") or [{}])[0].get("url")
                    if not image_url:
                        raise ValueError("dashscope 任务成功但无图片 URL")
                    img_resp = await client.get(image_url)
                    img_resp.raise_for_status()
                    return img_resp.content
                if status in ("FAILED", "CANCELED", "UNKNOWN"):
                    raise ValueError(f"dashscope 任务失败: {output.get('message', status)}")
                await asyncio.sleep(_POLL_INTERVAL_S)
            raise ValueError("dashscope 任务轮询超时")

    async def _stability(self, api_key: str, base_url: str, prompt: str, model: str = "sd3") -> bytes:
        url = f"{_STABILITY_API}/{model}"
        async with _new_client() as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Accept": "image/*"},
                files={"prompt": (None, prompt)},
                data={"size": "1024x1024"},
            )
            resp.raise_for_status()
            return resp.content


_DEFAULT_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "dashscope": "https://dashscope.aliyuncs.com",
    "stability": "https://api.stability.ai",
}

_PROVIDER_HANDLERS: dict[str, Callable[..., Awaitable[bytes]]] = {
    "openai": ImageService._openai,
    "dashscope": ImageService._dashscope,
    "stability": ImageService._stability,
}

image_service = ImageService()

__all__ = ["ImageResult", "ImageService", "image_service"]
