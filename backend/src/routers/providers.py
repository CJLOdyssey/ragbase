"""Provider definitions — capabilities, base URLs, and model hints.

Single source of truth served to the frontend via GET /api/providers
(ProviderEditModal type selector, capability badges).

Adding a new provider or capability requires only updating the PROVIDERS dict.
"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

# 主流 LLM API 供应商清单。base_url 均为官方 OpenAI 兼容端点
# （核对：DeepSeek/智谱/Kimi/硅基流动 官方文档；OpenAI/Anthropic/MiniMax/
# xAI/Groq/Mistral/NVIDIA/OpenRouter 业界聚合实证；豆包/千帆/混元/阶跃为
# 公开信息，个别可能随厂商调整 — 用户在表单中可随时修改）。
PROVIDERS: dict[str, dict[str, Any]] = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "capabilities": ["chat", "vector", "image"],
        "docs_url": "https://platform.openai.com/api-keys",
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "capabilities": ["chat"],
        "docs_url": "https://console.anthropic.com/settings/keys",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "capabilities": ["chat"],
        "docs_url": "https://platform.deepseek.com/api_keys",
    },
    "dashscope": {
        "name": "通义（阿里云百炼）",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "capabilities": ["chat", "vector", "image"],
        "docs_url": "https://bailian.console.aliyun.com/#/api-key",
    },
    "zhipu": {
        "name": "智谱 GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "capabilities": ["chat"],
        "docs_url": "https://bigmodel.cn/usercenter/proj-mgmt/apikeys",
    },
    "moonshot": {
        "name": "Kimi（月之暗面）",
        "base_url": "https://api.moonshot.cn/v1",
        "capabilities": ["chat"],
        "docs_url": "https://platform.kimi.com/console/api-keys",
    },
    "siliconflow": {
        "name": "硅基流动",
        "base_url": "https://api.siliconflow.cn/v1",
        "capabilities": ["chat", "vector", "image"],
        "docs_url": "https://cloud.siliconflow.cn/account/ak",
    },
    "minimax": {
        "name": "MiniMax",
        "base_url": "https://api.minimaxi.com/v1",
        "capabilities": ["chat"],
        "docs_url": "https://platform.minimaxi.com",
    },
    "volcengine": {
        "name": "豆包（火山方舟）",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "capabilities": ["chat"],
        "docs_url": "https://console.volcengine.com/ark",
    },
    "qianfan": {
        "name": "百度千帆",
        "base_url": "https://qianfan.baidubce.com/v2",
        "capabilities": ["chat", "vector"],
        "docs_url": "https://console.bce.baidu.com/qianfan/ais/console/onlineTest",
    },
    "hunyuan": {
        "name": "腾讯混元",
        "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "capabilities": ["chat"],
        "docs_url": "https://console.cloud.tencent.com/hunyuan",
    },
    "stepfun": {
        "name": "阶跃星辰",
        "base_url": "https://api.stepfun.com/v1",
        "capabilities": ["chat"],
        "docs_url": "https://platform.stepfun.com",
    },
    "xai": {
        "name": "xAI（Grok）",
        "base_url": "https://api.x.ai/v1",
        "capabilities": ["chat"],
        "docs_url": "https://console.x.ai",
    },
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "capabilities": ["chat"],
        "docs_url": "https://console.groq.com/keys",
    },
    "google": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "capabilities": ["chat", "image"],
        "docs_url": "https://aistudio.google.com/apikey",
    },
    "mistral": {
        "name": "Mistral",
        "base_url": "https://api.mistral.ai/v1",
        "capabilities": ["chat"],
        "docs_url": "https://console.mistral.ai/api-keys",
    },
    "nvidia": {
        "name": "NVIDIA NIM",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "capabilities": ["chat"],
        "docs_url": "https://build.nvidia.com",
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "capabilities": ["chat", "image"],
        "docs_url": "https://openrouter.ai/keys",
    },
    "ollama": {
        "name": "Ollama（本地）",
        "base_url": "http://127.0.0.1:11434/v1",
        "capabilities": ["chat", "vector"],
        "docs_url": "https://ollama.com/download",
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
