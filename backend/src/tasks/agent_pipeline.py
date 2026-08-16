"""Single-agent pipeline — tool discovery, RAG context, and graph execution."""

# ruff: noqa: E402 — imports after tracemalloc setup are intentional
import asyncio
import contextlib
import gc
import os
import subprocess
import time
import tracemalloc
from typing import Any

from broker import publish_run_message, publish_user_event
from checkpoint import close_checkpointer, create_checkpointer_async
from core.config import load_config
from core.infra.logging_config import get_logger
from graph.graph import SingleAgentGraph
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from repository import (
    get_messages,
    get_run_ancestors,
    get_session_memories,
    get_session_messages,
    list_attachments_by_run,
    update_message_content,
    update_run_result,
    update_run_status,
)
from repository.keys import log_key_usage
from streaming.emitter import StreamEmitter

from .pipeline_utils import (
    _build_session_context,
    _get_rag_context,
    _save_output_memories,
    log_memory_diff,
)

logger = get_logger(__name__)

_run_counter = 0
_AGENT_TIMEOUT = int(os.environ.get("AGENT_TIMEOUT", "600"))  # 10 minutes default


async def _notify_session_changed(user_id: str, session_id: str | None) -> None:
    """Broadcast a session update to other clients (cross-client sync). Fail-open."""
    if not session_id or not user_id:
        return
    try:
        await publish_user_event(
            user_id,
            {
                "type": "session.updated",
                "session_id": session_id,
                "ts": int(time.time()),
            },
        )
    except Exception:
        logger.debug("session sync notify failed for %s", session_id, exc_info=True)


def _guard_input(requirement: str) -> list[str]:
    """OWASP LLM01 input filtering.

    Hidden control/zero-width characters in a user message are never
    legitimate — reject hard. Instruction markers (visible text) pass
    through; the caller logs them as suspicious.
    """
    from rag.rag_guard import scan_document

    reasons = scan_document(requirement)
    if any("zero-width/control" in r for r in reasons):
        raise ValueError("输入包含不可见控制字符，已拒绝")
    return reasons


def _flag_output(text: str) -> list[str]:
    """OWASP LLM01 output filtering: flag model answers carrying injection
    markers (log + warning event only — an answer may legitimately quote one)."""
    from rag.rag_guard import scan_document

    return scan_document(text)


async def _enforce_token_budget(user_id: str, run_id: str) -> bool:
    """OWASP LLM10 unbounded-consumption guard.

    Rolling 24h token budget per user (USER_DAILY_TOKEN_BUDGET env, 0 =
    disabled). Over budget → run fails loud with a user-facing error.
    """
    budget = int(os.environ.get("USER_DAILY_TOKEN_BUDGET", "0"))
    if budget <= 0 or user_id == "system":
        return True
    from datetime import UTC, datetime, timedelta

    from repository.keys_crud import sum_user_tokens_since

    used = await sum_user_tokens_since(
        user_id, datetime.now(UTC) - timedelta(days=1)
    )
    if used < budget:
        return True
    logger.warning(
        "[GUARD] user %s over 24h token budget %d (used %d)",
        user_id, budget, used,
    )
    with contextlib.suppress(Exception):
        await update_run_status(run_id, "error")
    with contextlib.suppress(Exception):
        await publish_run_message(
            run_id,
            {
                "type": "error",
                "message": f"近 24 小时 LLM 用量已达上限（{budget} tokens），请稍后或联系管理员",
            },
        )
    return False


def _kill_stuck_child_processes() -> None:
    """Kill any OS-level child processes left behind by a timed-out task.

    ``asyncio.timeout`` cancels the coroutine but does **not** kill child
    OS processes spawned by libraries (e.g. multiprocessing forks inside
    LangGraph).  Those orphans continue burning CPU indefinitely.
    """
    try:
        ppid = os.getpid()
        # 无 shell 形式：ppid 是 os.getpid() 的 int，但避免 shell 拼接（bandit B605）
        with subprocess.Popen(
            ["ps", "--ppid", str(ppid), "-o", "pid=", "--no-headers"],
            stdout=subprocess.PIPE,
            text=True,
        ) as pipe:
            children = pipe.stdout.read().strip().split() if pipe.stdout else []
        for pid_str in children:
            if not pid_str.strip():
                continue
            pid = int(pid_str)
            try:
                with open(f"/proc/{pid}/cmdline") as f:
                    cmd = f.read().replace("\0", " ")
                if "multiprocessing.spawn" in cmd:
                    logger.warning("[TASKS] Killing stuck child PID %d (cmd=%s…)", pid, cmd[:80])
                    os.kill(pid, 9)
            except (ProcessLookupError, FileNotFoundError, PermissionError):
                pass
    except Exception:
        logger.exception("[TASKS] Failed to clean up child processes")


async def _run_agent_pipeline(
    requirement: str,
    run_id: str,
    session_id: str | None,
    api_key: str | None = None,
    api_base: str | None = None,
    model: str | None = None,
    user_id: str = 'system',
    image_model: bool = False,
) -> dict[str, Any]:
    global _run_counter
    _run_counter += 1
    if os.environ.get("MEM_TRACE", "").lower() in ("1", "true", "yes") and not tracemalloc.is_tracing():
        tracemalloc.start(25)
        logger.info("[MEM] tracemalloc started")
    # ponytail: tracemalloc snapshot/diff is heavy sync CPU work (500MB heap, 25
    # frames) — offload to a thread or it blocks the uvicorn event loop for 10s+
    # and POST /api/runs times out on the frontend's 10s axios limit.
    await asyncio.to_thread(log_memory_diff)
    logger.info("=== ENTER _run_agent_pipeline run=#%s | run=%s ===", _run_counter, run_id)
    await update_run_status(run_id, "running")
    cfg = load_config()

    # OWASP LLM01 input filter: hidden-control-char input fails loud before
    # any LLM/token spend; visible instruction markers are logged.
    for reason in _guard_input(requirement):
        logger.warning("[GUARD] input flagged: %s", reason)

    # OWASP LLM10: per-user rolling token budget — check before any LLM call.
    if not await _enforce_token_budget(user_id, run_id):
        return {"run_id": run_id, "status": "error"}

    effective_api_key = api_key
    effective_api_base = api_base
    effective_model = model or cfg.model

    system_prompt = ""

    session_context = ""
    rag_sources: list[dict[str, Any]] = []
    if session_id:
        try:
            # 分支树：记忆按当前 run 的父链过滤（MemoryEntry.run_id），
            # 并行分支的记忆不注入新分支上下文（编辑 ≠ 续写）。
            chain_ids = {r.id for r in await get_run_ancestors(run_id)}
            memories = [
                m for m in await get_session_memories(session_id)
                if m.run_id in chain_ids
            ]
            if memories:
                session_context = _build_session_context(memories)
            rag_ctx, rag_sources = await _get_rag_context(requirement, session_id, user_id)
            if rag_ctx:
                session_context += "\n" + rag_ctx
        except Exception:
            logger.warning("Failed to load RAG context for session %s", session_id)

    # ── Attachment context ────────────────────────────────────────
    # 附件在 create_run 时绑定 run_id，但此前只用于结果消息注入下载链接，
    # extracted_text 从未进模型输入 → 模型看不到文件内容。这里把当前 run
    # 绑定附件的文本提取结果拼入 session_context，让模型能读到文件。
    try:
        atts = await list_attachments_by_run(run_id)
        blocks = [
            f"[附件: {a.filename}]\n{a.extracted_text}"
            for a in atts
            if a.extracted_text and a.extracted_text.strip()
        ]
        if blocks:
            attachment_ctx = "\n\n".join(blocks)
            session_context = (
                session_context + "\n\n" + attachment_ctx
                if session_context
                else attachment_ctx
            )
    except Exception:
        logger.warning("Failed to load attachment context for run %s", run_id)

    # ── Short-term memory: parent-chain turns (branch-aware) ──
    chat_history: list[BaseMessage] = []
    if session_id:
        try:
            # 分支树：只回溯当前 run 的 parent 链（编辑分叉/续聊节点），
            # 不注入兄弟分支与选中节点之后的轮次。
            chain = await get_run_ancestors(run_id)
            for cr in chain[:-1]:  # 不含自身（自身 requirement 由 graph.run 追加）
                hist = await get_messages(cr.id)
                req = (cr.requirement or "").strip()
                # 去重：requirement 与 run 内首条 user 消息内容相同（常规轮次
                # 两者就是同一问题），只注入一次，省 token 不改变注入内容。
                first_user = next(
                    (m.content for m in hist if m.role == "user"), None
                )
                if req and req != (first_user or "").strip():
                    chat_history.append(HumanMessage(content=req))
                for m in hist:
                    if m.role == "user":
                        chat_history.append(HumanMessage(content=m.content))
                    elif m.role == "agent":
                        chat_history.append(AIMessage(content=m.content))
        except Exception:
            logger.warning("Failed to load branch history for run %s", run_id)

    checkpointer = await create_checkpointer_async()
    emitter = StreamEmitter(run_id, sources=rag_sources)
    graph = SingleAgentGraph(
        model=effective_model,
        api_key=effective_api_key or "",
        base_url=effective_api_base,
        checkpointer=checkpointer,
        image_model=image_model,
    )
    graph.set_stream_callback(emitter)

    try:
        async with asyncio.timeout(_AGENT_TIMEOUT):
            result = await graph.run(
                requirement=requirement,
                system_prompt=system_prompt,
                session_context=session_context,
                chat_history=chat_history,
                thread_id=run_id,
                run_id=run_id,
                no_rag_hits=not rag_sources,
            )
    except TimeoutError:
        logger.error("[TASKS] Agent pipeline timed out after %ds (run=%s)", _AGENT_TIMEOUT, run_id)
        await publish_run_message(run_id, {"type": "error", "message": "任务执行超时"})
        await update_run_status(run_id, "timeout")
        # Kill any OS child processes spawned by the timed-out task
        _kill_stuck_child_processes()
        await _notify_session_changed(user_id, session_id)
        return {"run_id": run_id, "status": "timeout"}
    except asyncio.CancelledError:
        # "停止生成"：task.cancel() 沿 await 链传播，上游 LLM 请求随之中断。
        logger.warning("[TASKS] Agent pipeline cancelled (run=%s)", run_id)
        # 半截内容也落库（只要有消息就入库）：取消时 emitter 中未 flush 的
        # 流式正文/思考保存为 chat_message，刷新后仍可见。
        with contextlib.suppress(Exception):
            await emitter.persist_partial()
        with contextlib.suppress(Exception):
            await update_run_status(run_id, "cancelled")
        await _notify_session_changed(user_id, session_id)
        with contextlib.suppress(Exception):
            await publish_run_message(run_id, {"type": "cancelled", "run_id": run_id})
        raise
    except Exception as exc:
        # LLM API failures (HTTPStatusError 402/401/429 etc.) must not leak out
        # of the task ("Task exception was never retrieved") nor leave the run
        # stuck in running. Surface an error event + mark the run failed.
        logger.error("[TASKS] Agent pipeline failed (run=%s): %s", run_id, exc)
        # 不向客户端透出原始异常（可能含 httpx URL/内部细节），详情在服务日志。
        await publish_run_message(run_id, {"type": "error", "message": "执行失败，请查看服务日志"})
        await update_run_status(run_id, "error")
        await _notify_session_changed(user_id, session_id)
        return {"run_id": run_id, "status": "error"}
    finally:
        # Postgres/sqlite checkpointers hold an open connection; close it on
        # every exit path (done, timeout, cancel, error) or each run leaks one.
        await close_checkpointer(checkpointer)
        # run 结束即释放 buffer pubsub 连接（不依赖 WS 断开/60s idle 兜底），
        # 防 Redis 池（REDIS_POOL_SIZE=20）耗尽 → MaxConnectionsError。
        try:
            from broker import stop_buffer

            await stop_buffer(run_id)
        except Exception:
            logger.debug("stop_buffer failed for run %s", run_id, exc_info=True)

    # ── Extract artifacts ──
    messages = result.get("messages", [])
    last_content = ""
    for m in reversed(messages):
        if hasattr(m, "content") and m.content:
            last_content = str(m.content)
            break

    # OWASP LLM01 output filter: a poisoned document may push the model into
    # emitting instructions — flag for audit, surface a warning event.
    output_reasons = _flag_output(last_content)
    if output_reasons:
        logger.warning("[GUARD] model output flagged: %s", "; ".join(output_reasons))
        with contextlib.suppress(Exception):
            await publish_run_message(
                run_id,
                {
                    "type": "warning",
                    "message": "回答疑似包含注入指令，已记录",
                    "reasons": output_reasons,
                },
            )

    # OWASP LLM02 / S5: PII in the model answer (leaked from indexed docs or
    # hallucinated) — audit + warning event, never silently altered.
    from rag.rag_pii import scan_pii

    pii_hits = scan_pii(last_content)
    if pii_hits:
        pii_types = sorted({h["type"] for h in pii_hits})
        logger.warning("[GUARD] model output contains PII: %s", ", ".join(pii_types))
        with contextlib.suppress(Exception):
            await publish_run_message(
                run_id,
                {
                    "type": "warning",
                    "message": "回答疑似包含敏感信息（PII），已记录",
                    "reasons": [f"pii:{t}" for t in pii_types],
                },
            )

    pm_document = ""
    code = last_content
    review = ""
    for m in messages:
        if hasattr(m, "content") and isinstance(m.content, str):
            if "<pm_document>" in m.content:
                pm_document = m.content
            if "<review>" in m.content:
                review = m.content

    try:
        await update_run_result(
            run_id=run_id,
            pm_document=pm_document,
            code=code,
            review=review,
            approved=True,
            status="converged",
        )
        await _notify_session_changed(user_id, session_id)
    except Exception:
        # 成功路径的落库/通知失败不得逃逸 task（同 LLM 失败处理：标记 error）。
        logger.error("[TASKS] Failed to persist converged result (run=%s)", run_id, exc_info=True)
        with contextlib.suppress(Exception):
            await publish_run_message(run_id, {"type": "error", "message": "结果保存失败，请查看服务日志"})
        with contextlib.suppress(Exception):
            await update_run_status(run_id, "error")
        return {"run_id": run_id, "status": "error"}

    # ── Attach download links to the final message ──
    # The model often references generated files by filename without a URL;
    # inject the /api/attachments links deterministically so the frontend can
    # offer a working download.
    try:
        atts = await list_attachments_by_run(run_id)
        if atts:
            links = [
                f"[📥 {a.filename}](/api/attachments/{a.id})"
                for a in atts
            ]
            block = "\n\n" + "\n".join(f"- {lnk}" for lnk in links)
            msg = await get_messages(run_id)
            if msg:
                last = msg[-1]
                if not any(a.id in (last.content or "") for a in atts):
                    await update_message_content(last.id, (last.content or "") + block)
    except Exception:
        logger.warning("Failed to attach download links for run %s", run_id, exc_info=True)

    # ── Save messages ── (now handled by save_response_action in agent_graph.py)

    # ── Long-term memory ──
    if session_id:
        await _save_output_memories(session_id, run_id, last_content, {})
        prev_msgs = await get_session_messages(session_id, exclude_run_id=run_id)
        if not prev_msgs:
            # First run for this session → ingest into RAG
            try:
                from rag.rag_pipeline import ingest_session_messages

                await ingest_session_messages(session_id, run_id, [{"content": requirement}], user_id=user_id)
            except Exception:
                logger.warning("RAG ingest failed for session %s", session_id)

    # ── Log key usage ──
    input_tokens = result.get("input_tokens", 0) or 0
    output_tokens = result.get("output_tokens", 0) or 0
    model_used = result.get("model", effective_model)
    try:
        provider = model_used.split("/")[0] if "/" in model_used else "deepseek"
        await log_key_usage(
            key_id=effective_api_key,
            user_id=user_id,
            run_id=run_id,
            provider=provider,
            model=model_used,
            tokens_prompt=input_tokens,
            tokens_completion=output_tokens,
        )
    except Exception:
        logger.warning("Failed to log key usage for run %s", run_id)

    await publish_run_message(
        run_id,
        {
            "type": "result",
            "status": "completed",
            "approved": True,
            "pm_document": pm_document,
            "code": code,
            "review": review,
        },
    )

    with contextlib.suppress(Exception):
        gc.collect()
    await asyncio.to_thread(log_memory_diff)
    logger.info("=== EXIT _run_agent_pipeline run=#%s | run=%s ===", _run_counter, run_id)
    return {"run_id": run_id, "status": "completed"}
