"""Task helper utilities."""
import asyncio
import contextlib
import json
import os
import threading
import tracemalloc
from typing import Any

from broker import publish_run_message
from core.infra.logging_config import get_logger
from core.mock_fallback import run_mock
from repository import (
    create_memory_entry,
    update_run_result,
    update_run_status,
)

logger = get_logger(__name__)

# ── Shared memory diagnostics ─────────────────────────────────────────────
_run_counter = 0
_baseline_snapshot: tracemalloc.Snapshot | None = None


def log_memory_diff() -> None:
    """Log current RSS and optional tracemalloc diff for leak detection."""
    global _baseline_snapshot
    try:
        pid = os.getpid()
        with open(f"/proc/{pid}/status") as f:
            rss_kb = int(f.read().split("VmRSS:")[1].split()[0])
        logger.info("[MEM] run=#%s pid=%s rss=%dKB", _run_counter, pid, rss_kb)
    except Exception:
        pass
    if not tracemalloc.is_tracing():
        return
    current = tracemalloc.take_snapshot()
    if _baseline_snapshot is None:
        _baseline_snapshot = current
        return
    diff = current.compare_to(_baseline_snapshot, "lineno")
    top = [str(d) for d in diff[:10] if d.size_diff > 0]
    if top:
        logger.info("[MEM] top growth:\n%s", "\n".join(top))
    _baseline_snapshot = current


# Thread-local event loop for celery threads-pool workers.
#
# WHY: asyncio.run() creates a fresh loop per task, but SQLAlchemy's async
# engine (QueuePool) and broker Redis pools are cached per-loop (or module-level).
# A fresh loop per task reuses connections created under a *closed* loop and
# blows up with "Future attached to a different loop" (or hangs on half-dead
# connections). Celery threads-pool runs tasks serially per thread, so caching
# one loop per thread is safe and lets pools stay valid across tasks.
_loop_local = threading.local()


def _run_async(coro: Any) -> Any:
    return asyncio.run(coro)


BALANCE_ERROR_KEYWORDS = [
    "insufficient_quota", "insufficient_balance", "insufficient balance", "余额不足",
    "billing limit", "quota exceeded", "payment required",
    "account balance", "402",
]


def _is_balance_error(exc: Exception) -> bool:
    """Check if the exception is caused by insufficient model balance/quota."""
    msg = str(exc).lower()
    return any(kw in msg for kw in BALANCE_ERROR_KEYWORDS)


def _report_run_error(run_id: str, exc: Exception) -> None:
    try:
        if _is_balance_error(exc):
            _run_async(
                publish_run_message(
                    run_id,
                    {
                        "type": "balance_warning",
                        "content": "模型余额不足，请检查 API Key 配置并确保账户有足够额度",
                    },
                )
            )
        _run_async(update_run_status(run_id, "error"))
        _run_async(
            publish_run_message(
                run_id,
                {
                    "type": "status",
                    "status": "error",
                    "error": str(exc),
                },
            )
        )
    except Exception:
        logger.exception("Failed to update error status for run %s", run_id)


def _try_mock_fallback(
    requirement: str, run_id: str, session_id: str | None, original_exc: Exception,
) -> dict[str, Any] | None:
    try:
        output = _run_async(run_mock(requirement, run_id, session_id))
        _run_async(
            update_run_result(
                run_id=run_id, pm_document="", code=output.response,
                review="LangGraph fallback", approved=True, status="converged",
            )
        )
        _run_async(
            publish_run_message(
                run_id,
                {"type": "result", "status": "completed", "approved": True,
                 "pm_document": "", "code": output.response, "review": "LangGraph fallback"},
            )
        )
        if session_id:
            with contextlib.suppress(Exception):
                _run_async(_save_output_memories(session_id, run_id, output.response, {}))
        return {"run_id": run_id, "status": "completed", "fallback": True}
    except Exception as mock_exc:
        logger.exception("Mock fallback also failed for run=%s", run_id)
        _report_run_error(run_id, original_exc)
        raise mock_exc


def _parse_json_field(field: Any) -> list[Any]:
    if isinstance(field, str):
        try:
            return json.loads(field) if field else []
        except (json.JSONDecodeError, TypeError):
            return []
    return field or []


def _build_session_context(memories: list[Any]) -> str:
    if not memories:
        return ""
    lines = ["\n\n【历史上下文】"]
    for m in memories:
        lines.append(f"- [{m.content_type}] {m.agent_role}: {m.summary}")
    return "\n".join(lines)


async def _get_rag_context(
    query: str,
    session_id: str,
    user_id: str = "anonymous",
    run_id: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Retrieve RAG context + structured sources for citation.

    Returns (plain-text context for the LLM, chunk-level source list for the
    message UI). On any failure: empty context, no sources — retrieval must
    never break the chat.
    """
    try:
        import time

        from rag.rag_pipeline import ensure_embedding_provider, retrieve_context, retrieve_sources
        from repository.keys import get_embedding_config

        cfg = await get_embedding_config()
        if cfg is None or cfg["api_key"] is None:
            return "", []
        ensure_embedding_provider(
            cfg["api_key"], model=cfg["model"], base_url=cfg["base_url"]
        )
        started = time.perf_counter()
        sources = await retrieve_sources(
            query=query, user_id=user_id, session_id=session_id, top_k=3, rerank=True
        )
        context = await retrieve_context(
            query=query, user_id=user_id, session_id=session_id, top_k=3, rerank=True
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        # OWASP LLM08: append-only retrieval activity log (query/sources/
        # latency/user) — best-effort, must never break the chat.
        with contextlib.suppress(Exception):
            from repository.retrieval_logs import create_retrieval_log

            await create_retrieval_log(
                user_id=user_id,
                session_id=session_id,
                run_id=run_id,
                query=query,
                latency_ms=latency_ms,
                hit_count=len(sources),
                sources=sources,
                top_k=3,
                rerank=True,
            )
        # O4: shadow variant replay (env-gated, best-effort) — separate table.
        with contextlib.suppress(Exception):
            await _run_shadow_retrieval(query, session_id, user_id)
        return context, sources
    except Exception:
        logger.warning("RAG context retrieval failed for session %s", session_id, exc_info=True)
        return "", []


async def _run_shadow_retrieval(
    query: str, session_id: str | None, user_id: str
) -> None:
    """O4: shadow retrieval — replay the query under a variant config.

    Enabled by env RAG_SHADOW_VARIANTS, e.g. "rerank:false,min_score:0.55"
    (key:value pairs overriding the primary config). Results go to the
    append-only shadow_retrieval_logs table — never into retrieval_logs,
    which would pollute the online monitoring metrics. Best-effort.
    """
    variants_raw = os.environ.get("RAG_SHADOW_VARIANTS")
    if not variants_raw:
        return
    kwargs: dict[str, Any] = {}
    for pair in variants_raw.split(","):
        key, _, value = pair.strip().partition(":")
        if not key or not value:
            continue
        if key == "rerank":
            kwargs["rerank"] = value.lower() == "true"
        elif key == "top_k":
            kwargs["top_k"] = int(value)
        elif key == "min_score":
            kwargs["min_score"] = float(value)
    if not kwargs:
        return

    import time

    from rag.rag_pipeline import retrieve_sources
    from repository.shadow_retrieval import create_shadow_log

    started = time.perf_counter()
    sources = await retrieve_sources(
        query=query,
        user_id=user_id,
        session_id=session_id,
        top_k=kwargs.get("top_k", 3),
        rerank=kwargs.get("rerank", True),
        min_score=kwargs.get("min_score"),
    )
    shadow_ms = int((time.perf_counter() - started) * 1000)
    await create_shadow_log(
        user_id=user_id,
        session_id=session_id,
        query=query,
        variant=variants_raw,
        latency_ms=shadow_ms,
        hit_count=len(sources),
        sources=sources,
        top_k=kwargs.get("top_k", 3),
        rerank=kwargs.get("rerank", True),
        min_score=kwargs.get("min_score"),
    )


async def _save_output_memories(session_id: str, run_id: str, response: str, metadata: dict[str, Any]) -> None:
    """Save a summary memory entry for a run's output."""
    summary = response[:200].replace("\n", " ")
    try:
        await create_memory_entry(
            session_id=session_id,
            run_id=run_id,
            agent_role="assistant",
            content_type="content",
            summary=summary,
            details=response[:2000],
        )
    except Exception:
        logger.exception("Failed to save memory for run %s", run_id)
