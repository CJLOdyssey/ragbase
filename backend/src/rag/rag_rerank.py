"""Cross-encoder reranking via OpenAI-compatible /rerank endpoints.

SiliconFlow (BAAI/bge-reranker-v2-m3) verified live: POST {base}/rerank
with {"model", "query", "documents", "top_n"} → results[{index, score}].
"""

import asyncio
import json
import urllib.request
from typing import Any

RERANK_MODEL = "BAAI/bge-reranker-v2-m3"


class RerankProvider:
    """Cross-encoder reranker over an OpenAI-compatible endpoint."""

    def __init__(self, api_key: str, base_url: str, model: str = RERANK_MODEL):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def rerank(
        self, query: str, documents: list[str], top_n: int
    ) -> list[int]:
        """Return the document indices ranked by relevance, best first."""
        if not documents or top_n <= 0:
            return list(range(len(documents)))
        return await asyncio.to_thread(self._rerank_sync, query, documents, top_n)

    def _rerank_sync(
        self, query: str, documents: list[str], top_n: int
    ) -> list[int]:
        body = json.dumps(
            {"model": self.model, "query": query, "documents": documents, "top_n": top_n}
        ).encode("utf-8")
        req = urllib.request.Request(f"{self.base_url}/rerank", data=body, method="POST")
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
            result = json.loads(resp.read().decode("utf-8"))

        ranked: list[dict[str, Any]] = result.get("results") or []
        if not ranked:
            raise RuntimeError("rerank response missing results")
        return [int(r["index"]) for r in ranked]
