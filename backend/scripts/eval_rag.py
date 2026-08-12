"""Offline RAG evaluation — retrieval metrics + RAGAS-style quality metrics.

Retrieval (default, no LLM): recall@k / MRR over the golden set — "does any
expected_snippet appear verbatim in the retrieved chunks", deterministic and
CI-stable.

--ragas adds RAGAS-style quality metrics (faithfulness / answer relevancy /
context precision / context recall) judged by the configured LLM (OpenAI-
compatible chat endpoint, e.g. SiliconFlow). Same metric definitions as
docs.ragas.io, implemented locally with zero new dependencies.

Usage (needs embedding key + live pgvector):
    DATABASE_URL=... PYTHONPATH=backend/src \
      uv run python backend/scripts/eval_rag.py --corpus docs/SPEC.md --golden backend/tests/eval/golden_qa.json
    # with rerank + RAGAS:
      ... --rerank --ragas

Metrics reported overall and split by case category (lexical vs semantic) —
the lexical split exists to prove the pg_trgm leg earns its keep on
codes/ids/spec names where dense vectors fail.
"""

import argparse
import asyncio
import json
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
        from rag.rag_pipeline import _rerank_results

        results = await _rerank_results(query, results, args.top_k)
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
        from rag.rag_pipeline import _rerank_results

        results = await _rerank_results(query, results, args.top_k)
    return results


async def _main(args: argparse.Namespace) -> int:
    cases = _load_golden(args.golden)
    if args.limit:
        cases = cases[: args.limit]
    corpus = _load_corpus(args.corpus)

    cfg = await get_embedding_config()
    if cfg is None or cfg["api_key"] is None:
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
        return {
            "cases": n,
            f"recall@{args.top_k}": round(hits / n, 3) if n else 0.0,
            "mrr": round(rr_sum / n, 3) if n else 0.0,
        }

    overall = await evaluate(cases)
    for category in ("lexical", "semantic"):
        sub = [c for c in cases if c.get("category") == category]
        if sub:
            overall[category] = await evaluate(sub)
    print(json.dumps(overall, ensure_ascii=False, indent=2))
    if args.fail_below:
        ok = all(float(v) >= args.fail_below for k, v in overall.items() if k in ("recall@5", "mrr"))
        if not ok:
            print(f"GATE FAILED: recall@5/mrr below {args.fail_below}", file=sys.stderr)
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", nargs="+", default=["docs/SPEC.md"])
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
    parser.add_argument("--fail-below", type=float, default=0.0, help="CI gate: exit 1 if recall@5/mrr below this")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_main(args)))


if __name__ == "__main__":
    main()
