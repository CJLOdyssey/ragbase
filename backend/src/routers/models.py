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


class ModelInfo(BaseModel):
    id: str
    label: str
    provider: str


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
        for model_id in k.get("models", []):
            if model_id in seen:
                continue
            seen.add(model_id)
            models.append(ModelInfo(id=model_id, label=model_id, provider=provider_label))

    return models


@router.get("/api/models", response_model=list[ModelInfo])
async def list_models(request: Request) -> Any:
    """Return available models from the user's active API keys."""
    user_id = get_user_id(request)
    return await _get_models_from_keys(user_id)
