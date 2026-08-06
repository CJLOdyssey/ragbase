"""Raw LLM streaming completion pipeline — used by "继续生成" flow."""

import gc
import os
import tracemalloc
from typing import Any

import httpx
from broker import publish_run_message
from core.config import load_config
from core.infra.logging_config import get_logger
from repository import update_run_result, update_run_status

from .prefix_completion import stream_prefix_completion

logger = get_logger(__name__)


_complete_counter = 0

async def _complete_pipeline(
    content: str,
    run_id: str,
    api_key: str,
    api_base: str | None = None,
    model: str | None = None,
    thinking: str | None = None,
) -> dict[str, Any] | None:

    global _complete_counter
    _complete_counter += 1
    try:
        pid = os.getpid()
        with open(f"/proc/{pid}/status") as f:
            rss_kb = int(f.read().split("VmRSS:")[1].split()[0])
        logger.info("[MEM] complete run=#%s pid=%s rss=%dKB", _complete_counter, pid, rss_kb)
    except Exception:
        pass
    if not tracemalloc.is_tracing():
        tracemalloc.start(25)

    cfg = load_config()
    effective_model = model or cfg.model

    await update_run_status(run_id, "running")

    base_url = (api_base or "https://api.deepseek.com").rstrip("/")

    if thinking:
        clean_base = base_url.rstrip("/beta")
        url = f"{clean_base}/beta/chat/completions"
    else:
        url = f"{base_url}/chat/completions"

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    if thinking:
        body = {
            "model": effective_model,
            "messages": [
                {"role": "user", "content": content},
                {"role": "assistant", "content": "", "reasoning_content": thinking, "prefix": True},
            ],
            "stream": True,
            "max_tokens": 16384,
        }
        base_lower = (api_base or "").lower()
        model_lower = (effective_model or "").lower()
        is_deepseek = "deepseek" in base_lower or "deepseek" in model_lower
        if is_deepseek:
            body["thinking"] = {"type": "enabled"}
    else:
        system_prompt = (
            "Continue the following text naturally. "
            "Output ONLY the continuation — no prefix, no analysis, no commentary, no meta-text. "
            "Do not repeat the input text."
        )
        prompt = f"{system_prompt}\n\n{content}"
        body = {
            "model": effective_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "max_tokens": 16384,
        }

    logger.info("[complete] Starting completion for run %s | model=%s", run_id, effective_model)

    try:
        full_content, thinking_chunks = await stream_prefix_completion(url, headers, body, run_id)
    except httpx.HTTPStatusError as e:
        logger.error("[complete] HTTP error for run %s: %s", run_id, e, exc_info=True)
        await update_run_status(run_id, "error")
        await publish_run_message(run_id, {"type": "error", "detail": f"LLM API 错误: {e}"})
        return None
    except Exception as e:
        logger.error("[complete] Stream failed for run %s: %s", run_id, e, exc_info=True)
        await update_run_status(run_id, "error")
        await publish_run_message(run_id, {"type": "error", "detail": f"续写失败: {e}"})
        return None

    if thinking_chunks:
        await publish_run_message(run_id, {
            "type": "thinking_done",
            "agent_name": "Agent",
            "thinking": "".join(thinking_chunks),
        })

    try:
        await update_run_result(
            run_id,
            pm_document="",
            code=content + full_content,
            review="",
            approved=False,
            status="completed",
        )
        await publish_run_message(run_id, {
            "type": "result",
            "status": "completed",
            "code": content + full_content,
            "pm_document": "",
            "review": "",
            "approved": False,
        })
        logger.info("[complete] Done for run %s (%d chars)", run_id, len(full_content))
    except Exception as e:
        logger.error("[complete] Save failed for run %s: %s", run_id, e, exc_info=True)
        await update_run_status(run_id, "error")
        await publish_run_message(run_id, {"type": "error", "detail": f"保存失败: {e}"})
    finally:
        gc.collect()
        try:
            pid = os.getpid()
            with open(f"/proc/{pid}/status") as f:
                rss_kb = int(f.read().split("VmRSS:")[1].split()[0])
            logger.info("[MEM] complete end run=#%s pid=%s rss=%dKB", _complete_counter, pid, rss_kb)
        except Exception:
            pass
    return None
