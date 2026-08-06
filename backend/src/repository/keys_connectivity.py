"""API key connectivity testing — verifying live keys against provider endpoints."""

import asyncio
import json
from typing import Any

from repository.keys_crud import get_api_key_for_use


async def test_api_key_connection(key_id: str, user_id: str) -> dict[str, Any]:
    """Test connectivity for a stored key. Does NOT return the key itself.

    Runs the blocking HTTP call in a thread pool to avoid blocking the event loop.
    """
    key_cfg = await get_api_key_for_use(key_id, user_id)
    if not key_cfg:
        return {"success": False, "message": "Key not found or inactive"}

    return await asyncio.to_thread(_test_connection_sync, key_cfg)


def _test_connection_sync(key_cfg: dict[str, Any]) -> dict[str, Any]:
    """Test API key connectivity synchronously via HTTP in a thread pool."""
    import urllib.request

    try:
        endpoints = {
            "openai": "https://api.openai.com/v1/models",
            "deepseek": "https://api.deepseek.com/v1/models",
            "anthropic": "https://api.anthropic.com/v1/models",
        }

        base_url = (key_cfg.get("base_url") or "").rstrip("/")

        if base_url:
            if base_url.endswith("/v1"):
                test_url = base_url + "/models"
            elif base_url.endswith("/v1/"):
                test_url = base_url[:-1] + "/models"
            else:
                test_url = base_url + "/v1/models"
        else:
            test_url = endpoints.get(key_cfg["provider"], "")

        if not test_url:
            return {"success": False, "message": "No base URL configured", "models": []}

        req = urllib.request.Request(test_url, method="GET")
        req.add_header("Authorization", f"Bearer {key_cfg['api_key']}")
        req.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
            if resp.status == 200:
                models = _parse_models_from_response(resp, key_cfg["provider"])
                return {"success": True, "message": "Connection successful", "models": models}
            return {"success": False, "message": f"HTTP {resp.status}", "models": []}
    except Exception as e:
        return {"success": False, "message": str(e), "models": []}


def _parse_models_from_response(resp: Any, provider: str) -> list[str]:
    """Extract model IDs from the provider's /models response."""
    try:
        body = json.loads(resp.read().decode())
        data = body.get("data", [])
        models = []
        for item in data:
            model_id = item.get("id", "")
            if model_id:
                models.append(model_id)
        return models
    except Exception:
        return []
