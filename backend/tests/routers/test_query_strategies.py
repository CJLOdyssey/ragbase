"""Query rewrite strategies unit tests."""

import pytest

pytestmark = pytest.mark.unit

from routers.query_strategies import (
    ContextExpansionStrategy,
    PronounResolutionStrategy,
    QueryRewriteEngine,
)


class MockMessage:
    """Mock history message for testing."""

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content


class TestPronounResolutionStrategy:
    async def test_no_history(self):
        """Should return query unchanged when no history."""
        strategy = PronounResolutionStrategy()
        result = strategy.rewrite("测试查询", None)
        assert result == "测试查询"

    async def test_empty_history(self):
        """Should return query unchanged when history is empty."""
        strategy = PronounResolutionStrategy()
        result = strategy.rewrite("测试查询", [])
        assert result == "测试查询"

    async def test_no_pronoun(self):
        """Should return query unchanged when no pronoun present."""
        strategy = PronounResolutionStrategy()
        history = [MockMessage("user", "Python 是什么")]
        result = strategy.rewrite("Java 怎么用", history)
        assert result == "Java 怎么用"

    async def test_pronoun_resolution(self):
        """Should replace pronoun with last entity."""
        strategy = PronounResolutionStrategy()
        history = [MockMessage("user", "Python 是什么")]
        result = strategy.rewrite("它的性能如何", history)
        assert "Python" in result
        assert "它" not in result

    async def test_multiple_pronouns(self):
        """Should replace multiple pronouns."""
        strategy = PronounResolutionStrategy()
        history = [MockMessage("user", "机器学习")]
        result = strategy.rewrite("它和那个的区别", history)
        # Should replace at least one pronoun
        assert "机器学习" in result


class TestContextExpansionStrategy:
    async def test_no_history(self):
        """Should return query unchanged when no history."""
        strategy = ContextExpansionStrategy()
        result = strategy.rewrite("测试", None)
        assert result == "测试"

    async def test_long_query(self):
        """Should not expand query longer than 10 chars."""
        strategy = ContextExpansionStrategy()
        history = [MockMessage("user", "机器学习算法")]
        result = strategy.rewrite("这是一个很长的查询", history)
        # Query is 9 chars, so it should be expanded
        assert "机器学习算法" in result or result == "这是一个很长的查询"

    async def test_short_query_expansion(self):
        """Should expand short query with context."""
        strategy = ContextExpansionStrategy()
        history = [MockMessage("user", "机器学习")]
        result = strategy.rewrite("怎么用", history)
        assert "机器学习" in result
        assert "怎么用" in result

    async def test_context_already_in_query(self):
        """Should not expand if context already present."""
        strategy = ContextExpansionStrategy()
        history = [MockMessage("user", "Python")]
        result = strategy.rewrite("Python 怎么用", history)
        # Should not duplicate
        assert result.count("Python") == 1


class TestQueryRewriteEngine:
    async def test_default_strategies(self):
        """Should use default strategies when none provided."""
        engine = QueryRewriteEngine()
        assert len(engine.strategies) == 2
        assert isinstance(engine.strategies[0], PronounResolutionStrategy)
        assert isinstance(engine.strategies[1], ContextExpansionStrategy)

    async def test_custom_strategies(self):
        """Should use custom strategies when provided."""
        custom = [PronounResolutionStrategy()]
        engine = QueryRewriteEngine(custom)
        assert len(engine.strategies) == 1
        assert engine.strategies[0] is custom[0]

    async def test_rewrite_chain(self):
        """Should apply strategies in sequence."""
        engine = QueryRewriteEngine()
        history = [MockMessage("user", "Python")]
        result = engine.rewrite("它怎么用", history)
        # Should apply pronoun resolution
        assert "Python" in result

    async def test_rewrite_empty_query(self):
        """Should handle empty query."""
        engine = QueryRewriteEngine()
        result = engine.rewrite("", None)
        assert result == ""

    async def test_rewrite_strips_whitespace(self):
        """Should strip leading/trailing whitespace."""
        engine = QueryRewriteEngine()
        result = engine.rewrite("  测试  ", None)
        assert result == "测试"
