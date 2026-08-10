"""Golden set integrity checks — no LLM, no DB.

Guards the eval baseline against drift: every expected_snippet must be a
verbatim substring of the declared corpus, so recall@k stays deterministic.
"""

import json
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parents[2]
GOLDEN = EVAL_DIR / "golden_qa.json"
SPEC = REPO_ROOT / "docs" / "SPEC.md"


def _load_golden() -> dict:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


class TestGoldenSet:
    def test_minimum_size(self):
        cases = _load_golden()["cases"]
        assert len(cases) >= _load_golden()["meta"]["minimum"]

    def test_fields_valid(self):
        for case in _load_golden()["cases"]:
            assert case["query"].strip(), f"empty query: {case}"
            assert case["expected_snippets"], f"no snippets: {case['query']}"
            assert all(s.strip() for s in case["expected_snippets"])
            assert case["category"] in ("lexical", "semantic")

    def test_snippets_exist_in_corpus(self):
        """Snippets must match the corpus verbatim — keeps recall deterministic."""
        corpus = SPEC.read_text(encoding="utf-8")
        for case in _load_golden()["cases"]:
            for snippet in case["expected_snippets"]:
                assert snippet in corpus, (
                    f"snippet not in {SPEC.name}: {snippet!r} (query: {case['query']})"
                )

    def test_no_duplicate_queries(self):
        queries = [c["query"] for c in _load_golden()["cases"]]
        assert len(queries) == len(set(queries))

    def test_both_categories_represented(self):
        cats = {c["category"] for c in _load_golden()["cases"]}
        assert cats == {"lexical", "semantic"}
