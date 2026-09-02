"""Query rewrite API tests (unit, in-memory sqlite).

Uses the shared routers/conftest.py fixtures.
"""

import pytest

pytestmark = pytest.mark.unit


class TestQueryRewriteAPI:
    async def test_rewrite_empty_query(self, client):
        """Empty query should return empty result."""
        response = client.post("/api/query/rewrite", json={"query": ""})
        assert response.status_code == 200
        data = response.json()
        assert data["originalQuery"] == ""
        assert data["rewrittenQuery"] == ""

    async def test_rewrite_no_history(self, client):
        """Query without history should return unchanged."""
        response = client.post("/api/query/rewrite", json={"query": "测试查询"})
        assert response.status_code == 200
        data = response.json()
        assert data["originalQuery"] == "测试查询"
        assert data["rewrittenQuery"] == "测试查询"

    async def test_rewrite_with_pronoun(self, client):
        """Query with pronoun should be resolved with context."""
        history = [
            {"role": "user", "content": "Python 是什么"},
            {"role": "assistant", "content": "Python 是一种编程语言"},
        ]
        response = client.post(
            "/api/query/rewrite",
            json={"query": "它的性能如何", "history": history},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["originalQuery"] == "它的性能如何"
        # Pronoun should be replaced
        assert "Python" in data["rewrittenQuery"] or "它的性能如何" in data["rewrittenQuery"]

    async def test_rewrite_short_query_expansion(self, client):
        """Short query should be expanded with context."""
        history = [
            {"role": "user", "content": "机器学习算法"},
        ]
        response = client.post(
            "/api/query/rewrite",
            json={"query": "怎么用", "history": history},
        )
        assert response.status_code == 200
        data = response.json()
        # Short query should be expanded
        assert len(data["rewrittenQuery"]) > len(data["originalQuery"])

    async def test_list_strategies(self, client):
        """Should list available rewrite strategies."""
        response = client.get("/api/query/strategies")
        assert response.status_code == 200
        data = response.json()
        assert "strategies" in data
        assert len(data["strategies"]) >= 2
        strategy_names = [s["name"] for s in data["strategies"]]
        assert "PronounResolutionStrategy" in strategy_names
        assert "ContextExpansionStrategy" in strategy_names
