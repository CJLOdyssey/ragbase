"""Celery task registry."""

import time
from collections.abc import Callable
from typing import Any, cast

from broker import celery_app
from core.infra.logging_config import get_logger
from core.mock_fallback import ENABLE as ENABLE_MOCK_FALLBACK

from .agent_pipeline import _run_agent_pipeline
from .complete_pipeline import _complete_pipeline
from .pipeline_utils import _report_run_error, _run_async, _try_mock_fallback

logger = get_logger(__name__)


def _task(*args: Any, **kwargs: Any) -> Callable[..., Any]:
    return cast(Callable[..., Any], celery_app.task(*args, **kwargs))


@_task(bind=True, max_retries=2, default_retry_delay=5)
def run_agent(
    self: Any,
    requirement: str,
    run_id: str | None = None,
    session_id: str | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
    model: str | None = None,
    user_id: str = "system",
) -> Any:
    t0 = time.time()
    logger.info(
        "Celery task START | run=%s | session=%s | model=%s | retry=%d",
        run_id, session_id, model, self.request.retries,
    )
    assert run_id is not None, "run_id must be provided"

    try:
        result = _run_async(
            _run_agent_pipeline(
                requirement,
                run_id,
                session_id,
                api_key=api_key,
                api_base=api_base,
                model=model,
                user_id=user_id,
            )
        )
        elapsed = time.time() - t0
        logger.info(
            "Celery task SUCCESS | run=%s | elapsed=%.2fs | retry=%d",
            run_id, elapsed, self.request.retries,
        )
        return result
    except Exception as exc:
        elapsed = time.time() - t0
        logger.exception(
            "Celery task FAIL | run=%s | elapsed=%.2fs | retry=%d",
            run_id, elapsed, self.request.retries,
        )

        if ENABLE_MOCK_FALLBACK:
            result = _try_mock_fallback(requirement, run_id, session_id, exc)
            if result:
                logger.info(
                    "Celery task MOCK_FALLBACK | run=%s | elapsed=%.2fs",
                    run_id, time.time() - t0,
                )
                return result

        _report_run_error(run_id, exc)
        self.retry(exc=exc)


@_task(bind=True, max_retries=2, default_retry_delay=5)
def complete_agent(
    self: Any,
    content: str,
    run_id: str,
    api_key: str,
    api_base: str | None = None,
    model: str | None = None,
    thinking: str | None = None,
    question: str | None = None,
) -> Any:
    t0 = time.time()
    logger.info(
        "Celery complete START | run=%s | model=%s | thinking=%s | retry=%d",
        run_id, model, bool(thinking), self.request.retries,
    )
    try:
        result = _run_async(
            _complete_pipeline(content, run_id, api_key, api_base, model, thinking, question)
        )
        elapsed = time.time() - t0
        logger.info(
            "Celery complete SUCCESS | run=%s | elapsed=%.2fs | retry=%d",
            run_id, elapsed, self.request.retries,
        )
        return result
    except Exception:
        elapsed = time.time() - t0
        logger.exception(
            "Celery complete FAIL | run=%s | elapsed=%.2fs | retry=%d",
            run_id, elapsed, self.request.retries,
        )
        raise
