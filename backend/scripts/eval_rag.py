"""Offline RAG evaluation — retrieval metrics + RAGAS-style quality metrics.

Retrieval (default, no LLM): recall@k / MRR over the golden set — "does any
expected_snippet appear verbatim in the retrieved chunks", deterministic and
CI-stable. Cases may declare ``negative_snippets`` (corpus verbatim text that
must NOT be retrieved for that query) — the reported negative_pass_rate gates
the precision side (Q4: irrelevant high-scoring chunks hurt answers).

--ragas adds RAGAS-style quality metrics (faithfulness / answer relevancy /
context precision / context recall) judged by the configured LLM (OpenAI-
compatible chat endpoint, e.g. SiliconFlow). Same metric definitions as
docs.ragas.io, implemented locally with zero new dependencies.

Embedding/rerank endpoints: EMBEDDING_API_KEY / RERANK_API_KEY (+ *_BASE_URL)
env wins, else the configured DB key; --embedding-model / --rerank-model override
the model (the ambient EMBEDDING_MODEL env is deliberately ignored — backend/.env
sets text-embedding-v3 for the DashScope legacy path, which would silently
break the SiliconFlow CI gate). CI passes env keys — no seeded row needed.

Usage (needs embedding key + live pgvector):
    DATABASE_URL=... PYTHONPATH=backend/src \
      uv run python backend/scripts/eval_rag.py \\
          --corpus backend/tests/eval/corpus/SPEC.md --golden backend/tests/eval/golden_qa.json
    # CI gate (bge-m3 embed + rerank, per-metric thresholds + negative precision):
      EMBEDDING_API_KEY=... RERANK_API_KEY=... \
      ... --rerank --recall-fail-below 0.97 --mrr-fail-below 0.9 --negative-fail-below 0.65
    # with RAGAS (needs an LLM-capable key):
      ... --ragas

Metrics reported overall and split by case category (lexical vs semantic) —
the lexical split exists to prove the pg_trgm leg earns its keep on
codes/ids/spec names where dense vectors fail.
"""

import argparse
import asyncio
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag.rag_chunking import semantic_chunk  # noqa: E402
from rag.rag_embedding import EmbeddingProvider  # noqa: E402
from rag.rag_store import PgVectorStore  # noqa: E402
from repository.keys import get_embedding_config, get_rerank_config  # noqa: E402

_EVAL_SESSION = "eval:corpus"
_RAGAS_LLM_MODEL = "deepseek-ai/DeepSeek-V4-Flash"
# Judge prompts: each must make the model emit a parseable verdict only.
_PROMPT_FAITHFULNESS = (
    "你是评估器。判断回答中的每个陈述能否被给定上下文支撑。"
    '严格只输出 JSON，例如 {"supported": 2, "total": 3}，禁止其他文字。'
)
_PROMPT_RELEVANCY = (
    "你是评估器。判断回答与问题的相关性。"
    "严格只输出一个 0 到 1 之间的数字，例如 0.85，禁止其他文字。"
)
_PROMPT_PRECISION = (
    "你是评估器。判断每个上下文片段是否与问题相关。"
    '严格只输出 JSON，例如 {"relevant": 4, "total": 5}，禁止其他文字。'
)
_PROMPT_RECALL = (
    "你是评估器。判断参考答案中的陈述是否被给定上下文覆盖。"
    '严格只输出 JSON，例如 {"covered": 2, "total": 2}，禁止其他文字。'
)




def _load_golden(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["cases"]


def _build_chunks(corpus: str, args: argparse.Namespace) -> list:
    from rag.rag_chunking import hierarchical_chunk

    if args.hierarchical:
        return hierarchical_chunk(corpus, session_id=_EVAL_SESSION, run_id=None)
    return semantic_chunk(corpus, session_id=_EVAL_SESSION, run_id=None)


def _load_corpus(paths: list[str]) -> str:
    text_parts = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            text_parts.extend(f.read_text(encoding="utf-8", errors="ignore") for f in sorted(p.glob("*.md")))
        else:
            text_parts.append(p.read_text(encoding="utf-8", errors="ignore"))
    return "\n\n".join(text_parts)


async def _retrieve(
    args: argparse.Namespace, provider: EmbeddingProvider, store: PgVectorStore, query: str
) -> list[dict]:
    if args.multi_rewrite:
        return await _retrieve_multi(args, provider, store, query)
    if args.rewrite:
        llm_cfg = await _resolve_llm_config()
        if llm_cfg:
            query = await _rewrite_query(llm_cfg, query)
    query_embedding = await provider.embed_query(query)
    results = await store.search(
        query_embedding,
        query_text=query,
        user_id=args.user_id,
        session_id=_EVAL_SESSION,
        top_k=20 if args.rerank else args.top_k,
    )
    if args.rerank and len(results) > args.top_k:
        results = await _rerank_eval(args, query, results)
    return results


async def _retrieve_multi(
    args: argparse.Namespace, provider: EmbeddingProvider, store: PgVectorStore, query: str
) -> list[dict]:
    """Multi-query retrieval: original query + LLM rewrite, both embedded and
    searched, fused by RRF. Keeps lexical precision (original) while adding
    semantic breadth (rewrite) — Azure agentic-retrieval pattern."""
    llm_cfg = await _resolve_llm_config()
    queries = [query]
    if llm_cfg:
        rewritten = await _rewrite_query(llm_cfg, query)
        if rewritten != query:
            queries.append(rewritten)
    legs: list[list[dict]] = []
    for q in queries:
        q_emb = await provider.embed_query(q)
        legs.append(
            await store.search(
                q_emb,
                query_text=q,
                user_id=args.user_id,
                session_id=_EVAL_SESSION,
                top_k=20 if args.rerank else args.top_k,
            )
        )
    from rag.rag_store import _rrf_fuse

    results = _rrf_fuse(legs, 20 if args.rerank else args.top_k)
    if args.rerank and len(results) > args.top_k:
        results = await _rerank_eval(args, query, results)
    return results


async def _resolve_embedding_config(args: argparse.Namespace) -> dict | None:
    """Embedding endpoint, preferring explicit env over DB keys.

    CI passes EMBEDDING_API_KEY (+ optional EMBEDDING_BASE_URL/MODEL) so the
    eval gate runs without seeding user_api_keys; locally we fall back to the
    configured DB key. --embedding-model overrides the model either way.
    """
    env_key = os.environ.get("EMBEDDING_API_KEY")
    if env_key:
        # Never inherit the ambient EMBEDDING_MODEL (e.g. backend/.env sets
        # text-embedding-v3 for the DashScope legacy path) — the model is the
        # CLI override or the built-in default only.
        return {
            "api_key": env_key,
            "base_url": os.environ.get("EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1"),
            "model": args.embedding_model or "BAAI/bge-m3",
        }
    cfg = await get_embedding_config()
    if cfg is None or cfg["api_key"] is None:
        return None
    if args.embedding_model:
        cfg["model"] = args.embedding_model
    return cfg


async def _resolve_rerank_config(args: argparse.Namespace) -> dict | None:
    """Rerank endpoint, preferring explicit env over DB keys (CI symmetry)."""
    env_key = os.environ.get("RERANK_API_KEY")
    if env_key:
        return {
            "api_key": env_key,
            "base_url": os.environ.get("RERANK_BASE_URL", "https://api.siliconflow.cn/v1"),
            "model": args.rerank_model or "BAAI/bge-reranker-v2-m3",
        }
    return await get_rerank_config()


async def _rerank_eval(args: argparse.Namespace, query: str, results: list[dict]) -> list[dict]:
    """Cross-encoder rerank with the eval-resolved endpoint; no-op when unavailable.

    Mirrors rag_pipeline._rerank_results but resolves the endpoint from env
    first, so the CI gate reranks without a seeded user_api_keys row.
    """
    cfg = await _resolve_rerank_config(args)
    if cfg is None or cfg["api_key"] is None:
        print("rerank requested but no rerank key configured — skipping", file=sys.stderr)
        return results
    from rag.rag_rerank import RerankProvider

    provider = RerankProvider(api_key=cfg["api_key"], base_url=cfg["base_url"], model=cfg["model"])
    indices = await provider.rerank(query, [r["text"] for r in results], top_n=args.top_k)
    by_index = {i: results[i] for i in range(len(results))}
    return [by_index[i] for i in indices if i in by_index]


def _negative_hits(results: list[dict], negatives: list[str]) -> bool:
    """True when any retrieved chunk contains any negative snippet."""
    return any(n in r["text"] for r in results for n in negatives)


async def _main(args: argparse.Namespace) -> int:
    cases = _load_golden(args.golden)
    if args.limit:
        cases = cases[: args.limit]
    corpus = _load_corpus(args.corpus)

    cfg = await _resolve_embedding_config(args)
    if cfg is None:
        print("no embedding API key configured — cannot run eval", file=sys.stderr)
        return 2

    provider = EmbeddingProvider(
        api_key=cfg["api_key"], model=cfg["model"], base_url=cfg["base_url"]
    )
    store = PgVectorStore()
    await store.clear_session(_EVAL_SESSION)

    chunks = _build_chunks(corpus, args)
    texts = [c.text for c in chunks]
    embeddings = await provider.embed(texts)
    for chunk, emb in zip(chunks, embeddings, strict=False):
        chunk.embedding = emb
    await store.add(chunks, user_id=args.user_id)
    print(f"indexed {len(chunks)} chunks from {len(args.corpus)} file(s)")

    if args.ragas:
        llm_cfg = await _resolve_llm_config()
        if llm_cfg is None:
            print("no LLM-capable key for RAGAS — run without --ragas", file=sys.stderr)
            return 2
        metrics = await _ragas_metrics(cases, args, provider, store, llm_cfg)
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
        return 0

    async def evaluate(selected: list[dict]) -> dict:
        hits, rr_sum, n = 0, 0.0, len(selected)
        neg_hits, neg_cases = 0, 0
        for case in selected:
            results = await _retrieve(args, provider, store, case["query"])
            found_at = next(
                (
                    i + 1
                    for i, row in enumerate(results)
                    if any(s in row["text"] for s in case["expected_snippets"])
                ),
                None,
            )
            if found_at:
                hits += 1
                rr_sum += 1.0 / found_at
            negatives = case.get("negative_snippets") or []
            if negatives:
                neg_cases += 1
                if _negative_hits(results, negatives):
                    neg_hits += 1
        metrics: dict = {
            "cases": n,
            f"recall@{args.top_k}": round(hits / n, 3) if n else 0.0,
            "mrr": round(rr_sum / n, 3) if n else 0.0,
        }
        if neg_cases:
            metrics["negative_pass_rate"] = round(1 - neg_hits / neg_cases, 3)
            metrics["negative_cases"] = neg_cases
        return metrics

    overall = await evaluate(cases)
    for category in ("lexical", "semantic"):
        sub = [c for c in cases if c.get("category") == category]
        if sub:
            overall[category] = await evaluate(sub)
    print(json.dumps(overall, ensure_ascii=False, indent=2))
    if args.recall_fail_below:
        recall = float(overall[f"recall@{args.top_k}"])
        if recall < args.recall_fail_below:
            print(
                f"GATE FAILED: recall@{args.top_k} {recall} below {args.recall_fail_below}",
                file=sys.stderr,
            )
            return 1
    if args.mrr_fail_below:
        mrr = float(overall["mrr"])
        if mrr < args.mrr_fail_below:
            print(f"GATE FAILED: mrr {mrr} below {args.mrr_fail_below}", file=sys.stderr)
            return 1
    if args.negative_fail_below:
        neg_rate = float(overall.get("negative_pass_rate", 1.0))
        if neg_rate < args.negative_fail_below:
            print(
                f"GATE FAILED: negative_pass_rate {neg_rate} below {args.negative_fail_below}",
                file=sys.stderr,
            )
            return 1
    return 0


# ---------------------------------------------------------------------------
# RAGAS-style quality metrics (local implementation, no ragas dependency)
# ---------------------------------------------------------------------------

def _chat_sync(base_url: str, api_key: str, model: str, messages: list[dict]) -> str:
    body = json.dumps({"model": model, "messages": messages, "temperature": 0}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions", data=body, method="POST"
    )
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=180) as resp:  # nosec B310
        result = json.loads(resp.read().decode("utf-8"))
    return result["choices"][0]["message"]["content"]


async def _chat(base_url: str, api_key: str, model: str, messages: list[dict]) -> str:
    return await asyncio.to_thread(_chat_sync, base_url, api_key, model, messages)


async def _rewrite_query(llm: dict, query: str) -> str:
    """Rewrite a question into retrieval-friendly form (keep codes/spec names)."""
    rewritten = await _chat(
        llm["base_url"], llm["api_key"], llm["model"],
        [
            {
                "role": "system",
                "content": (
                    "你是检索查询改写器。把问题改写成利于检索的形式："
                    "保留编号/专名原样，补充关键词。只输出改写后的查询，禁止解释。"
                ),
            },
            {"role": "user", "content": query},
        ],
    )
    return rewritten.strip() or query


def _ratio(text: str) -> float | None:
    """Parse an LLM verdict: 'n/total', JSON keys, or a bare float."""
    import re

    m = re.search(r"(\d+)\s*/\s*(\d+)", text)
    if m:
        total = int(m.group(2))
        return int(m.group(1)) / total if total else None
    m = re.search(r"\"(?:supported|relevant|covered|total)\"\s*:\s*(\d+)", text)
    if m:
        total = int(m.group(1))
        if total == 0:
            return None
        m2 = re.search(r"\"(?:supported|relevant|covered)\"\s*:\s*(\d+)", text)
        return int(m2.group(1)) / total if m2 else None
    m = re.search(r"0\.\d+", text)
    return float(m.group(0)) if m else None


async def _resolve_llm_config() -> dict | None:
    cfg = await get_rerank_config()
    if cfg and cfg["api_key"]:
        return {"api_key": cfg["api_key"], "base_url": cfg["base_url"], "model": _RAGAS_LLM_MODEL}
    emb = await get_embedding_config()
    if emb and emb["api_key"] and emb["base_url"]:
        return {"api_key": emb["api_key"], "base_url": emb["base_url"], "model": _RAGAS_LLM_MODEL}
    return None


async def _ragas_metrics(
    cases: list[dict],
    args: argparse.Namespace,
    provider: EmbeddingProvider,
    store: PgVectorStore,
    llm: dict,
) -> dict:
    scores = {"faithfulness": [], "answer_relevancy": [], "context_precision": [], "context_recall": []}
    for case in cases:
        contexts = [r["text"] for r in await _retrieve(args, provider, store, case["query"])]
        ctx_block = "\n\n---\n\n".join(f"[{i+1}] {c[:400]}" for i, c in enumerate(contexts))

        answer = await _chat(
            llm["base_url"], llm["api_key"], llm["model"],
            [
                {"role": "system", "content": "你是严格的事实型助手，只依据给定上下文回答。"},
                {"role": "user", "content": f"问题：{case['query']}\n\n上下文：\n{ctx_block}\n\n请回答。"},
            ],
        )
        scores["faithfulness"].append(
            _ratio(await _chat(
                llm["base_url"], llm["api_key"], llm["model"],
                [
                    {"role": "system", "content": _PROMPT_FAITHFULNESS},
                    {"role": "user", "content": f"回答：{answer}\n\n上下文：\n{ctx_block}"},
                ],
            )) or 0.0
        )
        scores["answer_relevancy"].append(
            _ratio(await _chat(
                llm["base_url"], llm["api_key"], llm["model"],
                [
                    {"role": "system", "content": _PROMPT_RELEVANCY},
                    {"role": "user", "content": f"问题：{case['query']}\n回答：{answer}"},
                ],
            )) or 0.0
        )
        scores["context_precision"].append(
            _ratio(await _chat(
                llm["base_url"], llm["api_key"], llm["model"],
                [
                    {"role": "system", "content": _PROMPT_PRECISION},
                    {"role": "user", "content": f"问题：{case['query']}\n\n上下文：\n{ctx_block}"},
                ],
            )) or 0.0
        )
        if case.get("expected_answer"):
            scores["context_recall"].append(
                _ratio(await _chat(
                    llm["base_url"], llm["api_key"], llm["model"],
                    [
                        {"role": "system", "content": _PROMPT_RECALL},
                        {"role": "user", "content": f"参考答案：{case['expected_answer']}\n\n上下文：\n{ctx_block}"},
                    ],
                )) or 0.0
            )

    def mean(vals: list[float]) -> float:
        return round(sum(vals) / len(vals), 3) if vals else 0.0

    return {
        "cases": len(cases),
        **{k: mean(v) for k, v in scores.items()},
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", nargs="+", default=["backend/tests/eval/corpus/SPEC.md"])
    parser.add_argument("--golden", type=Path, default=Path("backend/tests/eval/golden_qa.json"))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--user-id", default="eval")
    parser.add_argument("--hierarchical", action="store_true", help="chunk with child+parent hierarchy")
    parser.add_argument("--rerank", action="store_true", help="rerank candidates with cross-encoder")
    parser.add_argument("--ragas", action="store_true", help="run RAGAS-style quality metrics (needs LLM key)")
    parser.add_argument("--rewrite", action="store_true", help="rewrite queries with LLM before retrieval")
    parser.add_argument(
        "--multi-rewrite",
        action="store_true",
        help="multi-query retrieval: original + LLM rewrite fused by RRF",
    )
    parser.add_argument("--limit", type=int, default=0, help="evaluate only the first N cases (0 = all)")
    parser.add_argument(
        "--recall-fail-below", type=float, default=0.0, help="CI gate: exit 1 if recall@k below this (0 = disabled)"
    )
    parser.add_argument(
        "--mrr-fail-below",
        type=float,
        default=0.0,
        help="CI gate: exit 1 if mrr below this (0 = disabled)",
    )
    parser.add_argument(
        "--negative-fail-below",
        type=float,
        default=0.0,
        help="CI gate: exit 1 if negative_pass_rate below this (0 = disabled)",
    )
    parser.add_argument(
        "--embedding-model",
        default="",
        help="override the embedding model (e.g. Qwen/Qwen3-Embedding-0.6B)",
    )
    parser.add_argument(
        "--rerank-model",
        default="",
        help="override the reranker model (e.g. BAAI/bge-reranker-v2-m3)",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    raise SystemExit(asyncio.run(_main(args)))


if __name__ == "__main__":
    main()
