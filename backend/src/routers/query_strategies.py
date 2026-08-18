"""Query rewrite strategies — extensible rewrite rules using Strategy Pattern."""

import re
from abc import ABC, abstractmethod
from typing import Protocol

from core.infra.logging_config import get_logger

logger = get_logger(__name__)


class HistoryMessage(Protocol):
    """Protocol for history message to avoid circular imports."""
    role: str
    content: str


class RewriteStrategy(ABC):
    """Abstract base class for query rewrite strategies.
    
    Follows Open-Closed Principle: new strategies can be added without modifying existing code.
    """

    @abstractmethod
    def rewrite(self, query: str, history: list[HistoryMessage] | None) -> str:
        """Rewrite the query based on conversation history.
        
        Args:
            query: The original query to rewrite
            history: Conversation history messages
            
        Returns:
            The rewritten query
        """
        pass


class PronounResolutionStrategy(RewriteStrategy):
    """Resolves pronouns by replacing them with the most recent entity from history.
    
    Example:
        Query: "它的性能如何？"
        History: ["这个项目的架构是什么？"]
        Result: "这个项目的性能如何？"
    """

    _PRONOUNS = re.compile(r"(他|她|它|这个|那个|这些|那一个|这一个)")

    def _extract_last_entity(self, history: list[HistoryMessage]) -> str | None:
        """Extract the most recent entity from the last 2-3 messages."""
        recent = history[-3:] if len(history) >= 3 else history
        for msg in reversed(recent):
            if msg.role == "user" and msg.content.strip():
                content = msg.content.strip()
                if len(content) < 50:
                    return content
                words = content.split()
                if words:
                    return " ".join(words[:5])
        return None

    def rewrite(self, query: str, history: list[HistoryMessage] | None) -> str:
        if not history:
            return query

        if self._PRONOUNS.search(query):
            entity = self._extract_last_entity(history)
            if entity:
                rewritten = self._PRONOUNS.sub(entity, query)
                logger.debug("PronounResolution: %s -> %s", query, rewritten)
                return rewritten

        return query


class ContextExpansionStrategy(RewriteStrategy):
    """Expands short queries by prepending context keywords from history.
    
    Example:
        Query: "性能如何？"
        History: ["这个项目的架构是什么？"]
        Result: "这个项目 性能如何？"
    """

    def _extract_context_keywords(self, history: list[HistoryMessage]) -> str | None:
        """Extract context keywords from the last user message."""
        for msg in reversed(history):
            if msg.role == "user" and msg.content.strip():
                content = msg.content.strip()
                if len(content) < 30:
                    return content
                words = content.split()
                keywords = [w for w in words if len(w) > 1][:3]
                return " ".join(keywords) if keywords else None
        return None

    def rewrite(self, query: str, history: list[HistoryMessage] | None) -> str:
        if not history or len(query) >= 10:
            return query

        context = self._extract_context_keywords(history)
        if context and context not in query:
            rewritten = f"{context} {query}"
            logger.debug("ContextExpansion: %s -> %s", query, rewritten)
            return rewritten

        return query


class QueryRewriteEngine:
    """Orchestrates multiple rewrite strategies.
    
    Follows Dependency Inversion Principle: depends on abstract RewriteStrategy,
    not concrete implementations.
    """

    def __init__(self, strategies: list[RewriteStrategy] | None = None):
        """Initialize with a list of strategies.
        
        Args:
            strategies: List of rewrite strategies to apply in order.
                       If None, uses default strategies.
        """
        if strategies is None:
            # Default strategies in order of application
            self.strategies = [
                PronounResolutionStrategy(),
                ContextExpansionStrategy(),
            ]
        else:
            self.strategies = strategies

    def rewrite(self, query: str, history: list[HistoryMessage] | None) -> str:
        """Apply all strategies in sequence.
        
        Args:
            query: The original query
            history: Conversation history
            
        Returns:
            The final rewritten query
        """
        result = query
        for strategy in self.strategies:
            result = strategy.rewrite(result, history)
        return result.strip()


# Global engine instance with default strategies
_default_engine = QueryRewriteEngine()


def rewrite_query(query: str, history: list[HistoryMessage] | None) -> str:
    """Convenience function using the default engine.
    
    This maintains backward compatibility with existing code.
    """
    return _default_engine.rewrite(query, history)
