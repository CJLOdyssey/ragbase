"""Embedding provider for RAG pipeline (DashScope / OpenAI-compatible)."""

import asyncio
import json
import os
import urllib.request
from typing import Any

from core.infra.logging_config import get_logger

logger = get_logger(__name__)

EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-v3")
EMBEDDING_DIM = 1024  # text-embedding-v3 output dimension
DASHSCOPE_EMBEDDING_URL = (
    "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
)


class EmbeddingProvider:
    """Embedding via HTTP API — DashScope native or any OpenAI-compatible endpoint.

    base_url=None uses the legacy DashScope protocol (native request shape).
    base_url set (e.g. https://api.siliconflow.cn/v1) uses the OpenAI-compatible
    protocol: POST {base_url}/embeddings with {"model", "input": [...]}.
    """

    def __init__(
        self,
        api_key: str,
        model: str = EMBEDDING_MODEL,
        base_url: str | None = None,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Batch-embed a list of texts. Returns list of 1024-dim vectors.

        Raises RuntimeError on any failure — callers must handle; zero-vector
        fallback would silently poison the vector store with fake embeddings.
        """
        if not self.api_key:
            raise RuntimeError(
                "RAG embedding unavailable: no DashScope API key configured"
            )
        return await asyncio.to_thread(self._embed_sync, texts)

    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        """Embed texts synchronously via HTTP API in a thread pool."""
        if self.base_url:
            url = f"{self.base_url.rstrip('/')}/embeddings"
            body: dict[str, Any] = {"model": self.model, "input": texts}
            response_key = "data"
        else:
            url = DASHSCOPE_EMBEDDING_URL
            body = {
                "model": self.model,
                "input": {"texts": texts},
                "parameters": {"text_type": "document"},
            }
            response_key = "output.embeddings"

        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
            result = json.loads(resp.read().decode("utf-8"))

        if response_key == "data":
            embeddings = result.get("data") or []
            if not embeddings or "embedding" not in embeddings[0]:
                raise RuntimeError("embedding response missing embeddings")
            return [e["embedding"] for e in embeddings]

        if result.get("output") and result["output"].get("embeddings"):
            return [e["embedding"] for e in result["output"]["embeddings"]]
        raise RuntimeError("DashScope embedding response missing embeddings")

    async def embed_query(self, query: str) -> list[float]:
        embeddings = await self.embed([query])
        return embeddings[0]
