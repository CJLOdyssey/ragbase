"""Available models API route.

Returns the list of models that users can select in the frontend.
Models are read from the user_api_keys table — each active key contributes
its configured models to the available list.
"""

from typing import Any

from auth import get_user_id
from core.infra.logging_config import get_logger
from fastapi import APIRouter, Request
from pydantic import BaseModel
from repository import get_api_keys

logger = get_logger(__name__)
router = APIRouter(tags=["models"])

PROVIDER_LABELS = {
    "openai": "OpenAI",
    "deepseek": "DeepSeek",
    "anthropic": "Anthropic",
    "custom": "Custom",
}


EMBEDDING_PREFIXES = ("text-embedding", "embedding", "bge-", "m3e-", "jina-embeddings")
RERANK_PREFIXES = ("rerank", "bge-reranker")


def infer_model_type(model: str, provider: str) -> str:
    m = model.lower()
    if m.startswith(EMBEDDING_PREFIXES) or "embed" in m:
        return "embedding"
    if m.startswith(RERANK_PREFIXES):
        return "rerank"
    if m.startswith(("whisper", "paraformer", "sherpa")) or "asr" in m:
        return "speech2text"
    if m.startswith(("tts", "edge-tts")) or "voice" in m:
        return "tts"
    if "moderation" in m:
        return "moderation"
    if provider in ("tavily", "stability"):
        return "tool"
    return "llm"


class ModelInfo(BaseModel):
    id: str
    label: str
    provider: str
    type: str = "llm"


async def _get_models_from_keys(user_id: str) -> list[ModelInfo]:
    """Build model list from user's active API keys in the database."""
    try:
        keys = await get_api_keys(user_id)
    except Exception as e:
        logger.warning("Failed to load keys for model list: %s", e)
        return []

    seen: set[str] = set()
    models: list[ModelInfo] = []

    for k in keys:
        if not k.get("is_active"):
            continue
        provider = k.get("provider", "custom")
        provider_label = PROVIDER_LABELS.get(provider, provider.title())
        types_map = k.get("model_types") or {}
        for model_id in k.get("models", []):
            if model_id in seen:
                continue
            seen.add(model_id)
            models.append(
                ModelInfo(
                    id=model_id,
                    label=model_id,
                    provider=provider_label,
                    type=types_map.get(model_id) or infer_model_type(model_id, provider),
                )
            )

    return models


@router.get("/api/models", response_model=list[ModelInfo])
async def list_models(request: Request) -> Any:
    """Return available models from the user's active API keys."""
    user_id = get_user_id(request)
    return await _get_models_from_keys(user_id)
