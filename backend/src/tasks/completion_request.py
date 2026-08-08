"""Provider-aware continuation request builder — "继续生成" 三档分流.

Routes the continuation by API base capability:

- DeepSeek official (api.deepseek.com): Chat Prefix Completion (Beta)
  ``/beta/chat/completions`` + ``prefix: true`` + ``reasoning_content`` prefix.
- Kimi (api.moonshot.cn, kimi-k2*): Partial Mode — assistant message with
  ``partial: true`` (+ ``thinking.keep: "all"`` to carry reasoning back).
- Other OpenAI-compatible providers (SiliconFlow, …): plain context
  continuation via a standardized prompt template.

All three tiers receive the SAME normalized context — original question,
interrupted answer draft, interrupted reasoning draft — the difference is
only the transport mechanism (prefix / partial / prompt template).

Pure functions — no I/O, trivially unit-testable.
"""

from dataclasses import dataclass
from typing import Any

from core.infra.logging_config import get_logger

logger = get_logger(__name__)

DEEPSEEK_OFFICIAL_HOST = "api.deepseek.com"
MOONSHOT_HOST = "api.moonshot.cn"
DEFAULT_API_BASE = f"https://{DEEPSEEK_OFFICIAL_HOST}"

_MAX_TOKENS = 16384

# ── Standardized continuation context (what the model gets to see) ──────────


@dataclass(frozen=True)
class ContinuationContext:
    """The normalized input every tier hands to the model.

    question — the original user message the draft answers.
    draft    — the interrupted answer text (empty when only reasoning exists).
    thinking — the interrupted reasoning chain (empty when no reasoning).
    """

    question: str | None = None
    draft: str = ""
    thinking: str | None = None

    @property
    def has_draft(self) -> bool:
        return bool(self.draft.strip())

    @property
    def has_thinking(self) -> bool:
        return bool(self.thinking and self.thinking.strip())


# ── Standardized task instructions (behavior matrix) ────────────────────────
# draft 有 → 继续补全回答文本；draft 空 + thinking 有 → 续推思考后出正文。

_CONTINUE_DRAFT_INSTRUCTION = (
    "Continue the following answer draft naturally. "
    "Output ONLY the continuation — no prefix, no analysis, no commentary, no meta-text. "
    "Do not repeat the draft text."
)

_CONTINUE_THINKING_INSTRUCTION = (
    "The answer text was not produced yet; the reasoning was interrupted. "
    "Continue the reasoning from where it stopped, then output the final answer text. "
    "Output ONLY the answer at the end — no meta-text, no repetition of the draft reasoning."
)


def _render_fallback_prompt(ctx: ContinuationContext) -> str:
    """Render the standardized prompt for plain-continuation providers.

    Sections are omitted when their input is absent; the task instruction
    follows the behavior matrix (draft present → continue text; otherwise
    continue reasoning then emit the answer).
    """
    parts: list[str] = []
    if ctx.question:
        parts.append(f"<用户问题>\n{ctx.question}")
    if ctx.has_draft:
        parts.append(f"<已生成的回答草稿>\n{ctx.draft}")
    if ctx.has_thinking:
        parts.append(f"<已生成的思考草稿>\n{ctx.thinking}")
    instruction = (
        _CONTINUE_DRAFT_INSTRUCTION
        if ctx.has_draft
        else _CONTINUE_THINKING_INSTRUCTION
    )
    parts.append(f"<任务>\n{instruction}")
    return "\n\n".join(parts)


# ── Request types ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CompletionRequest:
    url: str
    headers: dict[str, str]
    body: dict[str, Any]


def build_completion_request(
    ctx: ContinuationContext,
    model: str | None,
    api_base: str | None,
    api_key: str,
) -> CompletionRequest:
    """Build the continuation (url, headers, body) routed by provider capability."""
    base = (api_base or DEFAULT_API_BASE).rstrip("/")
    effective_model = model or ""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    model_lower = effective_model.lower()

    if DEEPSEEK_OFFICIAL_HOST in base and ctx.has_thinking:
        return _deepseek_prefix_request(base, effective_model, ctx, headers)
    if MOONSHOT_HOST in base and ctx.has_thinking and "kimi-k2" in model_lower:
        return _kimi_partial_request(base, effective_model, ctx, headers)
    return _plain_continuation_request(base, effective_model, ctx, headers)


def _deepseek_prefix_request(
    base: str,
    model: str,
    ctx: ContinuationContext,
    headers: dict[str, str],
) -> CompletionRequest:
    """DeepSeek official Chat Prefix Completion (Beta).

    Official contract: last message must be ``assistant`` with ``prefix: True``
    and its ``content`` set to the already-generated prefix; the user message
    carries the original question. Reasoning chain is passed back via
    ``reasoning_content`` for seamless continuation of thinking models.
    """
    clean_base = base.rstrip("/beta")
    body: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "user", "content": ctx.question or "请继续完成下面的回答"},
            {
                "role": "assistant",
                "content": ctx.draft,
                "reasoning_content": ctx.thinking,
                "prefix": True,
            },
        ],
        "stream": True,
        "max_tokens": _MAX_TOKENS,
    }
    if "deepseek" in model.lower():
        body["thinking"] = {"type": "enabled"}
    return CompletionRequest(
        url=f"{clean_base}/beta/chat/completions",
        headers=headers,
        body=body,
    )


def _kimi_partial_request(
    base: str,
    model: str,
    ctx: ContinuationContext,
    headers: dict[str, str],
) -> CompletionRequest:
    """Kimi Partial Mode (Prefill): assistant prefill + preserved thinking.

    With a non-empty draft the model continues from the prefill; with an empty
    draft (thinking-only interruption) the prefill is skipped and the half-built
    reasoning chain drives the final answer.
    """
    assistant: dict[str, Any] = {
        "role": "assistant",
        "content": ctx.draft,
        "partial": ctx.has_draft,
        "reasoning_content": ctx.thinking,
    }
    user_prompt = (
        "请自然续写以下内容：" if ctx.has_draft else "基于以下思考过程，直接输出最终回答正文："
    )
    body: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "user", "content": ctx.question or user_prompt},
            assistant,
        ],
        "stream": True,
        "max_tokens": _MAX_TOKENS,
    }
    if "kimi-k2" in model.lower():
        body["thinking"] = {"type": "enabled", "keep": "all"}
    return CompletionRequest(
        url=f"{base}/chat/completions",
        headers=headers,
        body=body,
    )


def _plain_continuation_request(
    base: str,
    model: str,
    ctx: ContinuationContext,
    headers: dict[str, str],
) -> CompletionRequest:
    """Universal fallback: standardized prompt, no native prefix mechanism.

    - Draft interrupted mid-answer: continue the text, thinking disabled so
      the continuation run does not emit a fresh reasoning chain that would
      overwrite the message's thinking in the UI.
    - Draft interrupted mid-reasoning: thinking stays ENABLED so the reasoning
      chain keeps streaming from the break point (seamless in the UI) before
      the answer text is produced.
    """
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": _render_fallback_prompt(ctx)}],
        "stream": True,
        "max_tokens": _MAX_TOKENS,
    }
    if "siliconflow.cn" in base:
        body["enable_thinking"] = not ctx.has_draft
    else:
        body["thinking"] = {"type": "enabled" if not ctx.has_draft else "disabled"}
    return CompletionRequest(
        url=f"{base}/chat/completions",
        headers=headers,
        body=body,
    )
