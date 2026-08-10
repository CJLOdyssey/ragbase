"""Embedding provider for RAG pipeline (DashScope)."""

import asyncio
import json
import os
import urllib.request

from core.infra.logging_config import get_logger

logger = get_logger(__name__)

EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-v3")
EMBEDDING_DIM = 1024  # text-embedding-v3 output dimension


class EmbeddingProvider:
    """DashScope embedding via HTTP API — no heavy SDK dependency required."""

    def __init__(self, api_key: str, model: str = EMBEDDING_MODEL):
        self.api_key = api_key
        self.model = model
        self._base_url = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"

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
        """Embed texts synchronously via DashScope HTTP API in a thread pool."""

        body = json.dumps(
            {
                "model": self.model,
                "input": {"texts": texts},
                "parameters": {"text_type": "document"},
            }
        ).encode("utf-8")

        req = urllib.request.Request(self._base_url, data=body, method="POST")
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
            result = json.loads(resp.read().decode("utf-8"))

        if result.get("output") and result["output"].get("embeddings"):
            return [e["embedding"] for e in result["output"]["embeddings"]]
        raise RuntimeError("DashScope embedding response missing embeddings")

    async def embed_query(self, query: str) -> list[float]:
        embeddings = await self.embed([query])
        return embeddings[0]
