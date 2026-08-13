"""Graph helpers — context-guard template loading, balance detection, tool adapter."""

import contextlib
from typing import Any

from core._interfaces import ToolDescriptor, ToolExecutor
from core.infra.logging_config import get_logger

logger = get_logger(__name__)

# Identifier of the DB-stored context guard prompt (prompts table, editable +
# versioned via the prompts API — prompt text is NEVER hardcoded in code).
# Template holds a {context} placeholder; rendered around sanitized
# retrieval/attachment text at the injection boundary (OWASP LLM01).
CONTEXT_GUARD_PROMPT = "rag_context_guard"

# Deterministic refusal guidance injected ONLY when retrieval returned zero
# hits (no_rag_hits). Conditioned injection matters: the earlier
# unconditional "如上下文不足请说明" phrasing made the model conservative
# even WITH context (answer_relevancy 0.253 regression) — never inject this
# unless the pipeline has proof there is no knowledge-base context.
NO_RAG_HITS_PROMPT = (
    "【知识库检索结果】本次检索在知识库中未命中任何相关内容。"
    "若用户的问题需要知识库/文档内容才能回答，你必须明确说明无法基于知识库回答，"
    "不得编造或猜测来源；若为通用知识、闲聊或无需检索即可回答的问题，正常回答。"
)

# Balance/quota error keywords used to detect API billing failures
_BALANCE_ERROR_KEYWORDS = [
    "insufficient_quota", "insufficient_balance", "insufficient balance", "余额不足",
    "billing limit", "quota exceeded", "payment required", "account balance", "402",
]


async def _load_context_guard_template() -> str | None:
    """Fetch the active context-guard template from the prompts store."""
    from repository.prompts import get_prompts_as_dicts

    try:
        prompts = await get_prompts_as_dicts()
    except Exception:
        return None
    for p in prompts:
        if p.get("name") == CONTEXT_GUARD_PROMPT and p.get("status") == "active":
            return p.get("content")
    return None


def _is_balance_error(error_body: str) -> bool:
    """Check if the API error response indicates insufficient balance/quota."""
    body_lower = error_body.lower()
    return any(kw in body_lower for kw in _BALANCE_ERROR_KEYWORDS)


class _InlineToolExecutor(ToolExecutor):
    """Adapter that runs a ToolDescriptor through the tools node."""

    def __init__(self, tc: ToolDescriptor) -> None:
        self._tc = tc
        self.name = tc.name
        self.description = tc.description

    async def invoke(self, args: dict[str, Any]) -> str:
        execute = getattr(self._tc, "execute", None)
        if execute is None:
            return f"Unknown tool: {self.name}"
        result = await execute(args)
        return str(result)

    def set_llm(self, llm: Any) -> None:
        pass

    def set_run_id(self, run_id: str) -> None:
        pass


async def _emit_balance_warning(stream_cb: Any) -> None:
    """Emit a balance warning event to the frontend via the stream callback."""
    if hasattr(stream_cb, "emit_balance_warning"):
        await stream_cb.emit_balance_warning(
            "模型余额不足，请检查 API Key 配置并确保账户有足够额度"
        )
    else:
        # Fallback: emit as thinking event
        with contextlib.suppress(Exception):
            await stream_cb({
                "event": "on_custom_thinking",
                "data": {"content": "[warning] API 余额不足，请检查 API Key 配置"},
            })
