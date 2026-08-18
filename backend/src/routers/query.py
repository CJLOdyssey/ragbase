"""Query rewrite API — extensible query rewriting using Strategy Pattern."""

from typing import Any

from auth import get_user_id
from core.infra.logging_config import get_logger
from fastapi import APIRouter, Request
from pydantic import BaseModel
from pydantic.alias_generators import to_camel

from routers.query_strategies import QueryRewriteEngine, rewrite_query

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


@router.post("/api/query/rewrite", response_model=QueryRewriteOut)
async def rewrite_query_endpoint(req: QueryRewriteIn, request: Request) -> Any:
    """Rewrite a query using conversation history for context.

    Uses the Strategy Pattern to apply multiple rewrite rules:
    - PronounResolutionStrategy: Resolves pronouns with context from history
    - ContextExpansionStrategy: Expands short queries with context keywords

    New strategies can be added without modifying this endpoint (OCP).
    """
    user_id = get_user_id(request)
    original = req.query.strip()

    if not original:
        return QueryRewriteOut(rewritten_query=original, original_query=original)

    history = req.history or []
    rewritten = rewrite_query(original, history)

    logger.info(
        "Query rewrite | user=%s | session=%s | original=%s | rewritten=%s",
        user_id, req.session_id, original, rewritten,
    )

    return QueryRewriteOut(rewritten_query=rewritten, original_query=original)


@router.get("/api/query/strategies")
async def list_strategies() -> dict[str, Any]:
    """List available rewrite strategies for debugging/inspection."""
    engine = QueryRewriteEngine()
    return {
        "strategies": [
            {
                "name": strategy.__class__.__name__,
                "description": strategy.__class__.__doc__.strip().split("\n")[0] if strategy.__class__.__doc__ else "",
            }
            for strategy in engine.strategies
        ]
    }
