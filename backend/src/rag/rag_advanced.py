"""Advanced retrieval strategies — Query Decomposition and HyDE.

Query Decomposition:
    Breaks complex queries into sub-queries, retrieves for each, merges
    results.  Useful for multi-fact questions that need different retrieval
    paths (e.g. "What's the auth flow AND the deployment process?").

HyDE (Hypothetical Document Embeddings):
    Generates a hypothetical answer via LLM, embeds it, and uses that
    embedding for retrieval.  The hypothetical answer shares semantic
    space with real documents, improving recall for abstract queries.
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from core.infra.logging_config import get_logger

logger = get_logger(__name__)

_DECOMPOSE_MAX_SUB_QUERIES = int(os.environ.get("DECOMPOSE_MAX_SUB_QUERIES", "4"))
_HYDE_PROMPT_TEMPLATE = (
    "Write a short, factual passage (3-5 sentences) that would answer "
    "the following question.  Do NOT hallucinate — only write what you "
    "know to be true.  If you're unsure, write a general overview.\n\n"
    "Question: {query}"
)


async def _llm_chat(
    prompt: str,
    api_key: str,
    model: str | None = None,
    base_url: str | None = None,
    max_tokens: int = 500,
    temperature: float = 0.3,
) -> str:
    """Minimal LLM chat call via OpenAI-compatible API."""
    provider_model = model or "deepseek-ai/DeepSeek-V3"
    url = (base_url or "https://api.siliconflow.cn/v1") + "/chat/completions"

    body = {
        "model": provider_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
        result = json.loads(resp.read().decode("utf-8"))

    content: str = result["choices"][0]["message"]["content"]
    return content.strip()


# ── Query Decomposition ──────────────────────────────────────────────────────

_DECOMPOSE_PROMPT = (
    "Break the following query into {n} independent sub-queries that "
    "together fully answer it.  Return ONLY a JSON array of strings.\n\n"
    "Query: {query}\n\n"
    "Example: [\"sub-query 1\", \"sub-query 2\"]"
)


async def decompose_query(
    query: str,
    api_key: str,
    model: str | None = None,
    base_url: str | None = None,
    max_sub_queries: int = _DECOMPOSE_MAX_SUB_QUERIES,
) -> list[str]:
    """Decompose a complex query into independent sub-queries.

    Returns [original_query] on failure or if decomposition is unnecessary
    (short/simple queries).  The original query is always included so
    single-hop retrieval works even if decomposition fails.
    """
    # Skip decomposition for short queries — not worth the LLM call.
    if len(query.split()) < 8:
        return [query]

    prompt = _DECOMPOSE_PROMPT.format(n=max_sub_queries, query=query)

    try:
        response = await _llm_chat(prompt, api_key, model, base_url)
        # Parse JSON array from response
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        parsed = json.loads(text)
        if isinstance(parsed, list) and parsed:
            sub_queries = [str(q).strip() for q in parsed if str(q).strip()]
            # Always include original query for recall
            if query not in sub_queries:
                sub_queries.append(query)
            return sub_queries[:max_sub_queries + 1]
    except Exception:
        logger.exception("Query decomposition failed — falling back to original query")

    return [query]


# ── HyDE ─────────────────────────────────────────────────────────────────────

async def generate_hyde(
    query: str,
    api_key: str,
    model: str | None = None,
    base_url: str | None = None,
) -> str | None:
    """Generate a hypothetical document (answer) for HyDE retrieval.

    Returns None on failure — callers should fall back to the original query.
    """
    prompt = _HYDE_PROMPT_TEMPLATE.format(query=query)
    try:
        return await _llm_chat(prompt, api_key, model, base_url, max_tokens=200, temperature=0.7)
    except Exception:
        logger.exception("HyDE generation failed")
        return None


# ── Combined retrieval helper ────────────────────────────────────────────────

async def retrieve_with_advanced_strategies(
    query: str,
    search_fn: Any,
    api_key: str,
    model: str | None = None,
    base_url: str | None = None,
    use_decomposition: bool = True,
    use_hyde: bool = True,
    **search_kwargs: Any,
) -> list[dict[str, Any]]:
    """Retrieve using advanced strategies (decomposition + HyDE).

    This is a high-level orchestrator that wraps the existing search function:
    1. Decompose query into sub-queries (if complex enough)
    2. Generate HyDE for the original query (if enabled)
    3. Run retrieval for each sub-query + HyDE query
    4. Merge and deduplicate results by chunk id, keeping the best score
    """
    all_results: dict[str, dict[str, Any]] = {}

    # HyDE: generate hypothetical answer and retrieve with it
    if use_hyde:
        hyde_text = await generate_hyde(query, api_key, model, base_url)
        if hyde_text:
            try:
                hyde_results = await search_fn(hyde_text, **search_kwargs)
                for r in hyde_results:
                    rid = r.get("id", "")
                    if rid not in all_results or r.get("score", 0) > all_results[rid].get("score", 0):
                        all_results[rid] = r
            except Exception:
                logger.exception("HyDE retrieval failed")

    # Query Decomposition: retrieve for each sub-query
    sub_queries = [query]
    if use_decomposition:
        sub_queries = await decompose_query(query, api_key, model, base_url)

    for sq in sub_queries:
        try:
            results = await search_fn(sq, **search_kwargs)
            for r in results:
                rid = r.get("id", "")
                if rid not in all_results or r.get("score", 0) > all_results[rid].get("score", 0):
                    all_results[rid] = r
        except Exception:
            logger.exception("Sub-query retrieval failed: %s", sq[:80])

    # Sort by score descending
    merged = sorted(all_results.values(), key=lambda r: r.get("score", 0), reverse=True)
    top_k = search_kwargs.get("top_k", 5)
    return merged[:top_k]
