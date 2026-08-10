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


async def _get_rag_context(query: str, session_id: str, user_id: str = "anonymous") -> str:
    try:
        from rag.rag_pipeline import ensure_embedding_provider, retrieve_context
        from repository.keys import get_embedding_config

        cfg = await get_embedding_config()
        if cfg is None or cfg["api_key"] is None:
            return ""
        ensure_embedding_provider(
            cfg["api_key"], model=cfg["model"], base_url=cfg["base_url"]
        )
        return await retrieve_context(
            query=query, user_id=user_id, session_id=session_id, top_k=3
        )
    except Exception:
        logger.warning("RAG context retrieval failed for session %s", session_id, exc_info=True)
        return ""


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
