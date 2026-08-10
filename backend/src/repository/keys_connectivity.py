"""API key connectivity testing — verifying live keys against provider endpoints."""

import asyncio
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from repository.keys_crud import get_api_key_for_use
from domain.model_types import infer_model_type

# SiliconFlow /models sub_type filter values (official OpenAPI) → model type.
_SUB_TYPE_TO_MODEL_TYPE: dict[str, str] = {
    "chat": "llm",
    "embedding": "embedding",
    "reranker": "rerank",
    "text-to-image": "image",
    "image-to-image": "image",
    "text-to-video": "image",
    "speech-to-text": "speech2text",
}

# Audio models carry no sub_type; classify by name heuristic. ASR checked first
# because e.g. "SenseVoice" also matches the TTS "voice" marker.
_ASR_NAME_MARKERS = ("asr", "whisper", "paraformer", "sherpa", "sensevoice")
_TTS_NAME_MARKERS = ("tts", "voice", "speech", "cosyvoice", "edge-tts", "moss")

_FETCH_TIMEOUT = 15


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
        return {"success": False, "message": "No base URL configured", "models": [], "types": {}}

    success, models, types, message = _classify_models(
        test_url, key_cfg["api_key"], key_cfg["provider"]
    )
    return {"success": success, "message": message, "models": models, "types": types}


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


def _is_siliconflow(provider: str, base_url: str) -> bool:
    """True when the provider is SiliconFlow (name or base URL)."""
    provider_l = (provider or "").lower()
    base_l = (base_url or "").lower()
    return "硅基流动" in provider or "siliconflow" in provider_l or "siliconflow" in base_l


def _fetch_models_for_url(url: str, api_key: str) -> list[str]:
    """GET a /models-style endpoint with Bearer auth. Raises on HTTP error."""
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as resp:  # nosec B310
        if resp.status != 200:
            raise ConnectionError(f"HTTP {resp.status}")
        return _parse_models_from_response(resp, "siliconflow")


def _infer_audio_type(model_id: str) -> str:
    """Heuristic type for audio models that lack a sub_type: tts vs speech2text."""
    m = model_id.lower()
    if any(marker in m for marker in _ASR_NAME_MARKERS):
        return "speech2text"
    if any(marker in m for marker in _TTS_NAME_MARKERS):
        return "tts"
    return ""


def _classify_models(
    base_url: str, api_key: str, provider: str
) -> tuple[bool, list[str], dict[str, str], str]:
    """Fetch models in a single HTTP phase and map each to a model type.

    SiliconFlow: one request per sub_type filter plus a type=audio request,
    fetched concurrently. On ANY fetch failure, degrade to a single full-list
    request with an empty types map (pre-classification behavior); if the
    degrade request also fails, report failure with the underlying message.
    Other providers: single full-list request, types always empty.
    Returns (success, models, {model_id: type}, message).
    """

    def fetch_full() -> tuple[bool, list[str], dict[str, str], str]:
        try:
            models = _fetch_models_for_url(base_url, api_key)
            types = {m: infer_model_type(m, provider) for m in models}
            return True, models, types, "Connection successful"
        except Exception as e:
            return False, [], {}, str(e)

    if not _is_siliconflow(provider, base_url):
        return fetch_full()

    queries = {sub: f"{base_url}?sub_type={sub}" for sub in _SUB_TYPE_TO_MODEL_TYPE}
    queries["audio"] = f"{base_url}?type=audio"

    buckets: dict[str, list[str]] = {}
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(_fetch_models_for_url, url, api_key): key
                for key, url in queries.items()
            }
            buckets = {key: fut.result() for fut, key in futures.items()}
    except Exception:
        buckets = {}

    if not buckets:
        return fetch_full()

    models: list[str] = []
    types: dict[str, str] = {}
    seen: set[str] = set()
    for key, model_ids in buckets.items():
        model_type = "" if key == "audio" else _SUB_TYPE_TO_MODEL_TYPE[key]
        for model_id in model_ids:
            if model_id in seen:
                continue
            seen.add(model_id)
            models.append(model_id)
            if key == "audio":
                audio_type = _infer_audio_type(model_id)
                if audio_type:
                    types[model_id] = audio_type
            else:
                types[model_id] = model_type
    return True, models, types, "Connection successful"
