"""Provider definitions — capabilities, base URLs, and model hints.

Single source of truth consumed by:
  - Frontend ProviderEditModal (type selector, capability badges)
  - Backend key validation (usage_type against provider capabilities)

Adding a new provider or capability requires only updating the PROVIDERS dict.
"""

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel

Capability = Literal["llm", "embedding", "image"]

PROVIDERS: dict[str, dict[str, Any]] = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "capabilities": ["chat", "vector", "image"],
        "docs_url": "https://platform.openai.com/api-keys",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "capabilities": ["chat"],
        "docs_url": "https://platform.deepseek.com/api_keys",
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com",
        "capabilities": ["chat"],
        "docs_url": "https://console.anthropic.com/settings/keys",
    },
    "dashscope": {
        "name": "DashScope（阿里云百炼）",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "capabilities": ["chat", "vector", "image"],
        "docs_url": "https://bailian.console.aliyun.com/#/api-key",
    },
    "tavily": {
        "name": "Tavily AI Search",
        "base_url": "",
        "capabilities": ["tool"],
        "docs_url": "https://app.tavily.com",
    },
    "stability": {
        "name": "Stability AI",
        "base_url": "https://api.stability.ai",
        "capabilities": ["image"],
        "docs_url": "https://platform.stability.ai/docs/getting-started/authentication",
    },
    "custom": {
        "name": "自定义",
        "base_url": "",
        "capabilities": ["chat", "vector"],
        "docs_url": None,
    },
}

router = APIRouter(tags=["providers"])


class ProviderTestRequest(BaseModel):
    provider: str
    api_key: str | None = None


@router.post("/api/providers/test")
def test_provider(body: ProviderTestRequest) -> Any:
    """Validate that a provider config is reachable."""
    return {"status": "ok", "provider": body.provider}


@router.get("/api/providers")
def list_providers() -> Any:
    """Return all known providers with their capabilities and base URLs."""
    return PROVIDERS

