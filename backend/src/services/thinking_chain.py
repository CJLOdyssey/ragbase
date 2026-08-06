"""Thinking chain content builder — generates structured nodes for the agent's thinking chain display.

Encapsulates:
  - Config info block (system prompt, output constraints, tools, MCPs, skills)
  - Tool name classification for display prefixes
  - Result summary formatting
"""

from __future__ import annotations

import json
from typing import Any


def get_tool_prefix(tool_name: str) -> str:
    """Return display prefix for a tool name based on its category.

    - ``mcp_*`` → ``[mcp]``
    - ``skill_*`` → ``[skill]``
    - Other → ``[tools]``
    """
    if tool_name.startswith("mcp_"):
        return "[mcp]"
    if tool_name.startswith("skill_"):
        return "[skill]"
    return "[tools]"


def build_config_thinking(
    system_prompt: str,
    tool_definitions: list[dict[str, Any]],
) -> str:
    """Build the initial config-info text block for the thinking chain.

    Returns a multi-section block with sections separated by ``\\n\\n`` so
    that each section renders as a separate node in the frontend's thinking
    chain (which splits on ``/\\n{2,}/``).

    Returns an empty string if there is nothing to display.
    """
    segments: list[str] = []

    # ── System prompt & output constraints ──────────────────────
    if system_prompt:
        clean = system_prompt.strip()
        constraints = ""
        if "输出约束：" in clean:
            parts = clean.split("输出约束：", 1)
            clean = parts[0].strip()
            constraints = parts[1].strip()

        if clean:
            preview = clean.replace("\n", " ")[:120]
            if len(clean.replace("\n", " ")) > 120:
                preview += "..."
            segments.append(f"[info] 系统提示词\n{preview}")
        if constraints:
            segments.append(f"[info] 输出约束\n{constraints[:200]}")
    # ── Tool / MCP / Skill classification ───────────────────────
    tool_names: list[str] = [
        d.get("function", {}).get("name", "")
        for d in tool_definitions
    ]

    regular: list[str] = [
        n for n in tool_names
        if n and not n.startswith("mcp_") and not n.startswith("skill_")
    ]
    mcp_servers: set[str] = set()
    for n in tool_names:
        if n.startswith("mcp_") and "_" in n:
            parts = n.split("_", 2)
            if len(parts) >= 2:
                mcp_servers.add(parts[1])
    skill_names: list[str] = [
        n.split("_", 1)[1] for n in tool_names if n.startswith("skill_")
    ]

    if regular:
        segments.append(f"[tools] 可用工具\n{', '.join(regular)}")
    if mcp_servers:
        segments.append(f"[mcp] MCP 服务\n{', '.join(sorted(mcp_servers))}")
    if skill_names:
        segments.append(f"[skill] Skills\n{', '.join(skill_names)}")

    if not segments:
        return ""

    return "\n\n".join(segments) + "\n\n"


def format_result_preview(result: str | Any, max_len: int = 0) -> str:
    """Format tool result for display in thinking chain.

    When max_len > 0, truncate to that length; when 0 (default), return full text
    — frontend controls visual overflow via max-h + overflow-y-auto.
    """
    if isinstance(result, dict):
        # Strip fields already visible in [tools] line (tool name, query)
        preview = {k: v for k, v in result.items() if k not in ("tool", "query")}
        text = json.dumps(preview, ensure_ascii=False, default=str).strip()
    else:
        text = str(result or "").strip()
        # ToolWrapper.invoke serializes dicts to JSON string — try to parse and strip
        if text.startswith("{"):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    stripped = {k: v for k, v in parsed.items() if k not in ("tool", "query", "url")}
                    text = json.dumps(stripped, ensure_ascii=False, default=str).strip()
            except json.JSONDecodeError:
                pass
    if not text:
        return "(empty)"
    if 0 < max_len < len(text):
        return text[:max_len] + "..."
    return text
