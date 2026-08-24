"""Celery task registry."""

import time
from collections.abc import Callable
from typing import Any, cast

from broker import celery_app
from core.infra.logging_config import get_logger
from core.mock_fallback import ENABLE as ENABLE_MOCK_FALLBACK

from .agent_pipeline import _run_agent_pipeline
from .complete_pipeline import _complete_pipeline
from .health_snapshot import run_health_snapshot
from .index_asset import _index_asset
from .pipeline_utils import _report_run_error, _run_async, _try_mock_fallback
from .reindex_sweep import run_reindex_sweep

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
    prompt_id: str | None = None,
) -> Any:
    """Run the agent pipeline for a requirement in the background."""
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
                prompt_id=prompt_id,
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
def index_asset(
    self: Any,
    asset_id: str,
    user_id: str,
) -> Any:
    """Index an asset's chunks into pgvector — async, idempotent."""
    t0 = time.time()
    logger.info(
        "Celery index START | asset=%s | user=%s | retry=%d",
        asset_id, user_id, self.request.retries,
    )
    try:
        result = _run_async(_index_asset(asset_id, user_id))
        logger.info(
            "Celery index SUCCESS | asset=%s | elapsed=%.2fs | chunks=%s",
            asset_id, time.time() - t0, result.get("chunks"),
        )
        return result
    except Exception:
        logger.exception(
            "Celery index FAIL | asset=%s | elapsed=%.2fs | retry=%d",
            asset_id, time.time() - t0, self.request.retries,
        )
        raise


@_task()
def reindex_sweep() -> Any:
    """Celery beat entry: queue reindexes for changed/unindexed assets."""
    result = run_reindex_sweep()
    logger.info("Celery reindex sweep | queued=%s", result.get("queued"))
    return result


@_task(bind=True, max_retries=2, default_retry_delay=30)
def health_snapshot(self: Any) -> Any:
    """Celery beat entry: persist hourly composite health-score snapshots."""
    result = run_health_snapshot()
    logger.info(
        "Celery health snapshot | users=%s | failed=%s | pruned=%s",
        result.get("users"), result.get("failed"), result.get("pruned"),
    )
    return result


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
    """Persist a completed run's final answer in the background."""
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
