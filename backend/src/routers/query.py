"""Query rewrite API — rule-based contextual query expansion."""

import re
from typing import Any

from auth import get_user_id
from core.infra.logging_config import get_logger
from fastapi import APIRouter, Request
from pydantic import BaseModel
from pydantic.alias_generators import to_camel

logger = get_logger(__name__)
router = APIRouter(tags=["query"])


class HistoryMessage(BaseModel):
    role: str
    content: str


class QueryRewriteIn(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    query: str
    history: list[HistoryMessage] | None = None
    session_id: str | None = None


class QueryRewriteOut(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    rewritten_query: str
    original_query: str


_PRONOUNS = re.compile(r"(他|她|它|这个|那个|这些|这些|那一个|这一个)")


def _extract_last_entity(history: list[HistoryMessage]) -> str | None:
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


def _extract_context_keywords(history: list[HistoryMessage]) -> str | None:
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


def _rewrite_query(query: str, history: list[HistoryMessage] | None) -> str:
    """Apply rule-based query rewriting with conversation context."""
    if not history:
        return query

    rewritten = query

    if _PRONOUNS.search(query):
        entity = _extract_last_entity(history)
        if entity:
            rewritten = _PRONOUNS.sub(entity, rewritten)
            logger.debug("Pronoun replaced: %s -> %s", query, rewritten)

    if len(query) < 10:
        context = _extract_context_keywords(history)
        if context and context not in rewritten:
            rewritten = f"{context} {rewritten}"
            logger.debug("Context prepended: %s -> %s", query, rewritten)

    return rewritten.strip()


@router.post("/api/query/rewrite", response_model=QueryRewriteOut)
async def rewrite_query(req: QueryRewriteIn, request: Request) -> Any:
    """Rewrite a query using conversation history for context."""
    user_id = get_user_id(request)
    original = req.query.strip()

    if not original:
        return QueryRewriteOut(rewritten_query=original, original_query=original)

    history = req.history or []
    rewritten = _rewrite_query(original, history)

    logger.info(
        "Query rewrite | user=%s | session=%s | original=%s | rewritten=%s",
        user_id, req.session_id, original, rewritten,
    )

    return QueryRewriteOut(rewritten_query=rewritten, original_query=original)
