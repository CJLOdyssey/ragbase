"""RunService — orchestrates run creation, continuation, and lifecycle.

Decouples HTTP routing (routers/runs.py) from run orchestration logic
(tasks/*, repository/*, broker.py).  Routers become thin HTTP adapters;
RunService holds the business process.
"""
# ▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲▼▲
from __future__ import annotations

import asyncio
import contextlib
import os
from typing import Any, cast

from broker import buffer_run_messages
from core.config import load_config
from core.infra.logging_config import get_logger
from repository import (
    create_session,
    get_api_key_for_model,
    get_api_key_for_use,
    get_default_api_key,
    get_messages,
    get_run,
    get_runs,
    get_session,
    save_message,
    update_run_status,
    update_session_title,
)

from services.text_utils import parse_json_list

logger = get_logger(__name__)

# "thread"（默认，进程内 asyncio.create_task，适合 dev）| "celery"（走 worker）
RUN_DISPATCH = os.environ.get("RUN_DISPATCH", "thread")


class RunService:
    """Business-logic facade for run creation and lifecycle.

    Callers (HTTP routers) are responsible for:
      - HTTP request/response marshalling
      - authentication (user_id extraction)
      - WebSocket lifecycle

    RunService handles everything else:
      - session management (create / lookup)
      - API key resolution from vault
      - run persistence
      - Redis buffer subscription
      - background task dispatching
    """

    def __init__(self) -> None:
        # In-process task registry (thread mode) — run_id → asyncio.Task.
        self._tasks: dict[str, asyncio.Task[Any]] = {}

    def _register_task(self, run_id: str, task: asyncio.Task[Any]) -> None:
        self._tasks[run_id] = task
        task.add_done_callback(lambda _t: self._tasks.pop(run_id, None))

    async def create_run(
        self,
        requirement: str,
        session_id: str | None,
        user_id: str,
        key_id: str | None = None,
        model: str | None = None,
        parent_run_id: str | None = None,
        attachment_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a run, resolve credentials, subscribe to buffer, dispatch pipeline.

        Returns a dict with ``run_id``, ``session_id``, ``status``.
        """
        from repository import create_run as db_create_run

        requirement = requirement.strip()
        config = load_config()

        # ── Session ─────────────────────────────────────────────────
        if session_id is None:
            sess = await create_session(title=requirement[:64], user_id=user_id, kind="normal")
            session_id = sess.id
        else:
            existing_sess = await get_session(session_id)
            if existing_sess is None:
                logger.warning("session_id=%s not found, creating new session", session_id)
                sess = await create_session(
                    title=requirement[:64], user_id=user_id, kind="normal"
                )
                session_id = sess.id

        # ── Key resolution ──────────────────────────────────────────
        api_key: str | None = None
        api_base: str | None = None
        effective_model = model or config.model
        image_model = False

        if key_id:
            key_entry = await get_api_key_for_use(key_id, user_id)
            if key_entry:
                api_key = key_entry.get("api_key")
                api_base = key_entry.get("base_url") or api_base
                image_model = (key_entry.get("model_types") or {}).get(effective_model) == "image"
        if not api_key and effective_model:
            model_key = await get_api_key_for_model(effective_model, user_id)
            if model_key:
                api_key = model_key.get("api_key")
                api_base = model_key.get("base_url") or api_base
                image_model = (model_key.get("model_types") or {}).get(effective_model) == "image"
        if not api_key:
            default_key = await get_default_api_key(user_id)
            if default_key:
                api_key = default_key["api_key"]
                api_base = default_key["base_url"] or api_base

        if not api_key:
            raise ValueError("请先在设置中配置 API Key")

        # ── Persist run ─────────────────────────────────────────────
        try:
            req_versions: list[str] | None = None
            if parent_run_id:
                parent = await get_run(parent_run_id)
                if parent:
                    # Version list INCLUDES the current requirement (enhanced chain).
                    # parent_versions, when present, already ends with parent.requirement,
                    # so only append this run's requirement. On the FIRST edit
                    # parent_versions is empty — seed it with parent.requirement (the
                    # previous version) so the history isn't lost and nothing duplicates.
                    parent_versions = parse_json_list(parent.requirement_versions)
                    base = parent_versions if parent_versions else [parent.requirement]
                    req_versions = base + [requirement]
            run_id = await db_create_run(
                requirement,
                session_id=session_id,
                parent_run_id=parent_run_id,
                requirement_versions=req_versions,
            )
        except Exception as e:
            logger.error("Failed to create run: %s", e, exc_info=True)
            raise

        # ── Bind pre-uploaded attachments ─────────────────────────────
        # Pre-uploaded files (POST /api/attachments) carry session_id but no
        # run_id; binding happens here so the pipeline can inject their links.
        if attachment_ids:
            try:
                from repository.attachments import bind_attachments_to_run

                await bind_attachments_to_run(attachment_ids, run_id, session_id, user_id)
                logger.info(
                    "Attachments bound | run=%s | requested=%d",
                    run_id, len(attachment_ids),
                )
            except Exception:
                logger.exception("Failed to bind attachments for run=%s", run_id)

        # ── Persist user message ─────────────────────────────────────
        # 只要有消息就入库：用户问题也落库 chat_messages（此前仅存 runs.
        # requirement，加载时由 with_requirement_message 运行时合成）。
        # 该函数幂等保护：若消息已存在则跳过。
        try:
            await save_message(
                run_id=run_id,
                role="user",
                agent_name="我",
                content=requirement,
                round_number=1,
            )
        except Exception:
            logger.warning("Failed to persist user message for run %s", run_id)

        # ── Update session timestamp ────────────────────────────────
        try:
            existing_sess = await get_session(session_id)
            if existing_sess:
                await update_session_title(session_id, existing_sess.title)
        except Exception:
            pass

        # ── Redis buffer (subscribe *before* task starts) ───────────
        await buffer_run_messages(run_id)

        # ── Dispatch pipeline ───────────────────────────────────────
        try:
            if RUN_DISPATCH == "celery":
                from tasks import registry as _reg

                _reg.run_agent.delay(
                    requirement=requirement, run_id=run_id, session_id=session_id,
                    api_key=api_key, api_base=api_base,
                    model=effective_model, user_id=user_id,
                )
                logger.info("Task -> celery | run=%s", run_id)
                return {"run_id": run_id, "status": "pending", "session_id": session_id}

            # thread 模式：进程内后台任务
            from tasks import _run_agent_pipeline

            task = asyncio.create_task(
                _run_agent_pipeline(
                    requirement=requirement,
                    run_id=run_id,
                    session_id=session_id,
                    api_key=api_key,
                    api_base=api_base,
                    model=effective_model,
                    user_id=user_id,
                    image_model=image_model,
                )
            )
            self._register_task(run_id, task)
            logger.info(
                "Task started (thread) | run_id=%s | session_id=%s | model=%s",
                run_id, session_id, effective_model,
            )
        except Exception:
            logger.exception("Failed to start agent task for run=%s", run_id)
            await update_run_status(run_id, "error")
            raise

        return {"run_id": run_id, "status": "pending", "session_id": session_id}

    async def continue_run(
        self,
        content: str,
        session_id: str | None,
        user_id: str,
        thinking: str | None = None,
        model: str | None = None,
        question: str | None = None,
    ) -> dict[str, Any]:
        """Create a continuation run ("继续生成") — streams raw LLM output.

        Unlike ``create_run``, this bypasses the LangGraph pipeline and
        runs the completion directly in the uvicorn process via
        ``_complete_pipeline``. ``model`` is the model the user had selected
        in the conversation (falls back to the configured default model);
        ``question`` is the original user message the interrupted draft
        answers — needed by prefix/partial mechanisms for a seamless
        in-place continuation.
        """
        from repository import create_run as db_create_run

        config = load_config()

        # ── Session ─────────────────────────────────────────────────
        if session_id is None:
            title = (content or "续写")[:64]
            sess = await create_session(title=title, user_id=user_id)
            session_id = sess.id

        # ── Key resolution ──────────────────────────────────────────
        api_key: str | None = None
        api_base: str | None = None
        effective_model = model or config.model
        image_model = False

        try:
            if effective_model:
                model_key = await get_api_key_for_model(effective_model, user_id)
                if model_key:
                    api_key = model_key["api_key"]
                    api_base = model_key["base_url"]
                    image_model = (model_key.get("model_types") or {}).get(effective_model) == "image"
            if not api_key:
                default_key = await get_default_api_key(user_id)
                if default_key:
                    api_key = default_key["api_key"]
                    api_base = default_key["base_url"]
        except Exception:
            logger.warning("Key vault lookup failed in continue_run — using env var fallback")

        if not api_key:
            raise ValueError("请先在设置中配置 API Key")

        if image_model:
            raise ValueError("图片生成模型不支持继续生成")

        # ── Persist run ─────────────────────────────────────────────
        run_id = await db_create_run(content, session_id=session_id)

        # ── Persist user message ─────────────────────────────────────
        # 只要有消息就入库：续写 run 的用户消息 = 原问题（question）——
        # 视图显示「原问题 + 续写回答」，而非半截文本当问题。
        try:
            await save_message(
                run_id=run_id,
                role="user",
                agent_name="我",
                content=(question or content).strip() or content,
                round_number=1,
            )
        except Exception:
            logger.warning("Failed to persist user message for continuation run %s", run_id)

        # ── Redis buffer ────────────────────────────────────────────
        await buffer_run_messages(run_id)

        # ── Dispatch background pipeline ────────────────────────────
        if RUN_DISPATCH == "celery":
            from tasks import registry as _reg

            _reg.complete_agent.delay(
                content=content, run_id=run_id, api_key=api_key,
                api_base=api_base, model=effective_model, thinking=thinking,
                question=question,
            )
            logger.info("Complete -> celery | run=%s", run_id)
            return {"run_id": run_id, "status": "running", "session_id": session_id}

        async def _run_pipeline() -> Any:
            try:
                from tasks import _complete_pipeline

                await _complete_pipeline(
                    content=content,
                    run_id=run_id,
                    api_key=api_key,
                    api_base=api_base,
                    model=effective_model,
                    thinking=thinking,
                    question=question,
                )
            except asyncio.CancelledError:
                logger.warning("Complete pipeline cancelled for run=%s", run_id)
                await update_run_status(run_id, "cancelled")
            except Exception:
                logger.exception("Complete pipeline failed for run=%s", run_id)
                await update_run_status(run_id, "error")

        task = asyncio.create_task(_run_pipeline())
        self._register_task(run_id, task)

        return {"run_id": run_id, "status": "running", "session_id": session_id}

    async def cancel_run(self, run_id: str) -> dict[str, Any]:
        """Cancel an in-flight run — propagate cancellation to the LLM stream.

        Thread mode: ``task.cancel()`` unwinds the await chain and aborts the
        upstream httpx request; the pipeline marks the run ``cancelled``.
        Celery mode: best-effort revoke (no hard kill).
        """
        if RUN_DISPATCH == "celery":
            try:
                from broker import celery_app

                cast(Any, celery_app).control.revoke(run_id, terminate=False)
                await update_run_status(run_id, "cancelled")
                return {"run_id": run_id, "status": "cancelled", "cancelled": True}
            except Exception:
                logger.exception("Failed to revoke celery task run=%s", run_id)
                return {"run_id": run_id, "status": "pending", "cancelled": False}

        task = self._tasks.get(run_id)
        if task is None or task.done():
            run = await get_run(run_id)
            return {
                "run_id": run_id,
                "status": run.status if run else "not_found",
                "cancelled": False,
            }
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task
        await update_run_status(run_id, "cancelled")
        return {"run_id": run_id, "status": "cancelled", "cancelled": True}

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Fetch a single run by id."""
        run = await get_run(run_id)
        if run is None:
            return None
        messages = await get_messages(run_id)
        return {
            "id": run.id,
            "session_id": run.session_id,
            "requirement": run.requirement,
            "pm_document": run.pm_document,
            "code": run.code,
            "review": run.review,
            "approved": run.approved,
            "status": run.status,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "updated_at": run.updated_at.isoformat() if run.updated_at else None,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "agent_name": m.agent_name,
                    "content": m.content,
                    "thinking": m.thinking,
                    "round_number": m.round_number,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ],
        }

    async def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent runs."""
        runs = await get_runs(limit=min(limit, 100))
        return [
            {
                "id": r.id,
                "session_id": r.session_id,
                "requirement": r.requirement,
                "pm_document": r.pm_document,
                "code": r.code,
                "review": r.review,
                "approved": r.approved,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in runs
        ]


# Singleton for convenience (stateless service)
run_service = RunService()

__all__ = ["RunService", "run_service"]
