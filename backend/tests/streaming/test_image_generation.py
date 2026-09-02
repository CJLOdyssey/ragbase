"""Unit tests for image generation (SiliconFlow-style /images/generations)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from streaming.image_generation import ImageGenerationError, generate_image


def _mock_client(
    *,
    status: int = 200,
    json_payload: dict | None = None,
    text: str = "",
    exc: Exception | None = None,
) -> AsyncMock:
    client = AsyncMock()
    if exc is not None:
        client.post = AsyncMock(side_effect=exc)
    else:
        response = (
            httpx.Response(status, json=json_payload)
            if json_payload is not None
            else httpx.Response(status, text=text)
        )
        client.post = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    return client


def _patch_client(mock_client: AsyncMock):
    return patch("streaming.image_generation.httpx.AsyncClient", return_value=mock_client)


@pytest.mark.asyncio
async def test_generate_image_returns_url() -> None:
    client = _mock_client(json_payload={"images": [{"url": "https://img.example/a.png"}]})
    with _patch_client(client):
        url = await generate_image("sk-test", "a cat", model="Kwai-Kolors/Kolors")

    assert url == "https://img.example/a.png"


@pytest.mark.asyncio
async def test_generate_image_uses_provider_base_url() -> None:
    sent: dict = {}

    async def fake_post(url: str, headers: dict, json: dict) -> httpx.Response:
        sent["url"] = url
        sent["body"] = json
        return httpx.Response(200, json={"images": [{"url": "https://img.example/a.png"}]})

    client = AsyncMock()
    client.post = AsyncMock(side_effect=fake_post)
    client.__aenter__ = AsyncMock(return_value=client)
    with _patch_client(client):
        await generate_image(
            "sk-test", "a cat", model="Kwai-Kolors/Kolors", base_url="https://api.siliconflow.cn/v1"
        )

    assert sent["url"] == "https://api.siliconflow.cn/v1/images/generations"
    assert sent["body"]["model"] == "Kwai-Kolors/Kolors"
    assert sent["body"]["image_size"] == "1024x1024"
    assert sent["body"]["batch_size"] == 1


@pytest.mark.asyncio
async def test_generate_image_raises_on_http_error_status() -> None:
    client = _mock_client(status=400, text='{"code":20012}')
    with _patch_client(client):
        with pytest.raises(ImageGenerationError, match="400"):
            await generate_image("sk-test", "a cat", model="Kwai-Kolors/Kolors")


@pytest.mark.asyncio
async def test_generate_image_raises_when_images_missing() -> None:
    client = _mock_client(json_payload={"data": []})
    with _patch_client(client):
        with pytest.raises(ImageGenerationError, match="返回为空"):
            await generate_image("sk-test", "a cat", model="Kwai-Kolors/Kolors")


@pytest.mark.asyncio
async def test_generate_image_raises_on_transport_error() -> None:
    client = _mock_client(exc=httpx.ConnectError("refused"))
    with _patch_client(client):
        with pytest.raises(ImageGenerationError, match="请求失败"):
            await generate_image("sk-test", "a cat", model="Kwai-Kolors/Kolors")


@pytest.mark.asyncio
async def test_generate_image_raises_on_timeout() -> None:
    client = _mock_client(exc=httpx.ReadTimeout("read timed out"))
    with _patch_client(client):
        with pytest.raises(ImageGenerationError, match="请求失败"):
            await generate_image("sk-test", "a cat", model="Kwai-Kolors/Kolors")


@pytest.mark.asyncio
async def test_generate_image_propagates_cancellation() -> None:
    """Task cancel (asyncio.CancelledError) must propagate, not be wrapped."""
    import asyncio

    client = _mock_client(exc=asyncio.CancelledError())
    with _patch_client(client):
        with pytest.raises(asyncio.CancelledError):
            await generate_image("sk-test", "a cat", model="Kwai-Kolors/Kolors")


@pytest.mark.asyncio
async def test_generate_image_raises_on_non_json_body() -> None:
    client = _mock_client(text="<html>gateway error</html>")
    with _patch_client(client):
        with pytest.raises(ImageGenerationError, match="格式错误"):
            await generate_image("sk-test", "a cat", model="Kwai-Kolors/Kolors")


@pytest.mark.asyncio
async def test_generate_image_raises_when_image_missing_url() -> None:
    client = _mock_client(json_payload={"images": [{"foo": "bar"}]})
    with _patch_client(client):
        with pytest.raises(ImageGenerationError, match="缺少 URL"):
            await generate_image("sk-test", "a cat", model="Kwai-Kolors/Kolors")


@pytest.mark.asyncio
async def test_generate_image_passes_custom_params_and_strips_slash() -> None:
    sent: dict = {}

    async def fake_post(url: str, headers: dict, json: dict) -> httpx.Response:
        sent["url"] = url
        sent["body"] = json
        return httpx.Response(200, json={"images": [{"url": "https://img.example/a.png"}]})

    client = AsyncMock()
    client.post = AsyncMock(side_effect=fake_post)
    client.__aenter__ = AsyncMock(return_value=client)
    with _patch_client(client):
        await generate_image(
            "sk-test",
            "a dog",
            model="Kwai-Kolors/Kolors",
            base_url="https://api.siliconflow.cn/v1/",
            image_size="768x768",
            batch_size=2,
        )

    assert sent["url"] == "https://api.siliconflow.cn/v1/images/generations"
    assert sent["body"]["prompt"] == "a dog"
    assert sent["body"]["image_size"] == "768x768"
    assert sent["body"]["batch_size"] == 2
