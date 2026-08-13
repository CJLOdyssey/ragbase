"""Golden set integrity checks — no LLM, no DB.

Guards the eval baseline against drift: every expected_snippet must be a
verbatim substring of the declared corpus, so recall@k stays deterministic.
"""

import json
from pathlib import Path

import pytest

EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parents[2]
GOLDEN = EVAL_DIR / "golden_qa.json"
# Committed copy of docs/SPEC.md (docs/ is gitignored, so CI checkout has no
# SPEC.md) — guarded against drift by test_corpus_copy_in_sync_with_docs_spec.
CORPUS = EVAL_DIR / "corpus" / "SPEC.md"


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
        corpus = CORPUS.read_text(encoding="utf-8")
        for case in _load_golden()["cases"]:
            for snippet in case["expected_snippets"]:
                assert snippet in corpus, (
                    f"snippet not in {CORPUS.name}: {snippet!r} (query: {case['query']})"
                )

    def test_no_duplicate_queries(self):
        queries = [c["query"] for c in _load_golden()["cases"]]
        assert len(queries) == len(set(queries))

    def test_both_categories_represented(self):
        cats = {c["category"] for c in _load_golden()["cases"]}
        assert cats == {"lexical", "semantic"}

    def test_reference_answers_present(self):
        """RAGAS context_recall needs reference answers; guard the subset."""
        cases = _load_golden()["cases"]
        with_ref = [c for c in cases if c.get("expected_answer")]
        assert len(with_ref) >= _load_golden()["meta"]["reference_cases"]
        assert all(c["expected_answer"].strip() for c in with_ref)

    def test_negative_minimum_coverage(self):
        """Precision gate needs enough negative cases to be meaningful."""
        cases = _load_golden()["cases"]
        with_neg = [c for c in cases if c.get("negative_snippets")]
        assert len(with_neg) >= _load_golden()["meta"]["negative_minimum"]
        assert all(
            isinstance(c["negative_snippets"], list) and c["negative_snippets"]
            for c in with_neg
        )

    def test_negative_snippets_in_corpus(self):
        """Negatives must be corpus verbatim — otherwise they gate nothing."""
        corpus = CORPUS.read_text(encoding="utf-8")
        for case in _load_golden()["cases"]:
            for snippet in case.get("negative_snippets") or []:
                assert snippet in corpus, (
                    f"negative snippet not in {CORPUS.name}: {snippet!r} "
                    f"(query: {case['query']})"
                )

    def test_negative_not_overlapping_positive(self):
        """A snippet cannot be both expected and forbidden for the same query."""
        for case in _load_golden()["cases"]:
            pos = set(case["expected_snippets"])
            for snippet in case.get("negative_snippets") or []:
                assert snippet not in pos, (
                    f"snippet both expected and negative: {snippet!r} "
                    f"(query: {case['query']})"
                )

    def test_corpus_copy_in_sync_with_docs_spec(self):
        """Committed eval corpus must track docs/SPEC.md (source of truth).

        CI skips when docs/SPEC.md is absent (docs/ is gitignored and not in
        the checkout); locally the copy must match byte-for-byte so the golden
        set cannot drift from the spec.
        """
        source = REPO_ROOT / "docs" / "SPEC.md"
        if not source.exists():
            pytest.skip("docs/SPEC.md absent (gitignored) — CI runs against the committed copy")
        assert source.read_text(encoding="utf-8") == CORPUS.read_text(encoding="utf-8"), (
            "backend/tests/eval/corpus/SPEC.md diverged from docs/SPEC.md — "
            "copy the updated spec into the eval corpus"
        )
