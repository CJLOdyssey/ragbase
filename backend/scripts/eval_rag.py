"""Offline RAG retrieval evaluation — recall@k / MRR over the golden set.

No LLM involved: recall is "does any expected_snippet appear verbatim in the
retrieved chunks", so scores are deterministic and CI-stable.

Usage (needs DashScope embedding key + live pgvector):
    DATABASE_URL=... PYTHONPATH=backend/src \
      uv run python backend/scripts/eval_rag.py --corpus docs/SPEC.md --golden backend/tests/eval/golden_qa.json

Metrics reported overall and split by case category (lexical vs semantic) —
the lexical split exists to prove the pg_trgm leg earns its keep on
codes/ids/spec names where dense vectors fail.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag.rag_chunking import semantic_chunk  # noqa: E402
from rag.rag_embedding import EmbeddingProvider  # noqa: E402
from rag.rag_store import PgVectorStore  # noqa: E402
from repository.keys import get_embedding_config  # noqa: E402

_EVAL_SESSION = "eval:corpus"


def _load_golden(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["cases"]


def _load_corpus(paths: list[str]) -> str:
    text_parts = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            text_parts.extend(f.read_text(encoding="utf-8", errors="ignore") for f in sorted(p.glob("*.md")))
        else:
            text_parts.append(p.read_text(encoding="utf-8", errors="ignore"))
    return "\n\n".join(text_parts)


async def _main(args: argparse.Namespace) -> int:
    cases = _load_golden(args.golden)
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

    chunks = semantic_chunk(corpus, session_id=_EVAL_SESSION, run_id=None)
    texts = [c.text for c in chunks]
    embeddings = await provider.embed(texts)
    for chunk, emb in zip(chunks, embeddings, strict=False):
        chunk.embedding = emb
    await store.add(chunks, user_id=args.user_id)
    print(f"indexed {len(chunks)} chunks from {len(args.corpus)} file(s)")

    async def evaluate(selected: list[dict]) -> dict:
        hits, rr_sum, n = 0, 0.0, len(selected)
        for case in selected:
            query_embedding = await provider.embed_query(case["query"])
            results = await store.search(
                query_embedding,
                query_text=case["query"],
                user_id=args.user_id,
                session_id=_EVAL_SESSION,
                top_k=args.top_k,
            )
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
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", nargs="+", default=["docs/SPEC.md"])
    parser.add_argument("--golden", type=Path, default=Path("backend/tests/eval/golden_qa.json"))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--user-id", default="eval")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_main(args)))


if __name__ == "__main__":
    main()
