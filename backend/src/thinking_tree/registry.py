"""Tool registry — extensible plugin system for agent tools.

Architecture:
  Plugins register as handlers for specific tool names.
  Multiple handlers per tool name form a priority-based fallback chain.

  Execution flow:
    LLM calls "web_search"
      → registry.get_handlers("web_search")
      → [prio=100] tavily  (returns results)
      → [prio=50]  baidu   (fallback)
      → [prio=0]   bing    (last resort)

  Frontend discovery:
    GET /api/tools/plugins → registry.list_plugins()
    Returns plugin metadata including config_schema for dynamic form rendering.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

ToolHandler = Callable[[str, dict[str, Any]], Any]


class ToolRegistry:
    """Maps tool names to handler implementations.

    register_plugin() registers both a handler (for execution) and metadata
    (for frontend discovery).  register() is the low-level variant.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[tuple[int, ToolHandler]]] = {}
        self._plugin_infos: dict[str, dict[str, Any]] = {}

    # ── Registration ────────────────────────────────────────────────────

    def register(self, tool_name: str, handler: ToolHandler, priority: int = 0) -> None:
        """Low-level: register a handler for *tool_name*.

        Higher *priority* values are tried first in the fallback chain.
        """
        if tool_name not in self._handlers:
            self._handlers[tool_name] = []
        self._handlers[tool_name].append((priority, handler))
        self._handlers[tool_name].sort(key=lambda x: -x[0])

    def register_plugin(
        self,
        tool_name: str,
        handler: ToolHandler,
        *,
        label: str = "",
        description: str = "",
        config_schema: dict[str, Any] | None = None,
        priority: int = 0,
    ) -> None:
        """Register a full plugin with metadata for frontend discovery.

        Args:
            tool_name: The tool name this plugin handles (e.g. "web_search")
            handler: Async function(tool_name, args) -> dict
            label: Human-readable name for UI (e.g. "Tavily AI Search")
            description: What this plugin does
            config_schema: JSON Schema for frontend config form
            priority: Higher = tried first in fallback chain

        """
        self.register(tool_name, handler, priority=priority)
        existing = self._plugin_infos.get(tool_name)
        if not existing or priority > existing["_priority"]:
            self._plugin_infos[tool_name] = {
                "tool_name": tool_name,
                "label": label or tool_name,
                "description": description,
                "config_schema": config_schema,
                "_priority": priority,
                "_handler": handler,
            }

    # ── Execution routing ───────────────────────────────────────────────

    def lookup(self, tool_name: str) -> ToolHandler | None:
        """Return the highest-priority handler for *tool_name*."""
        handlers = self._handlers.get(tool_name, [])
        return handlers[0][1] if handlers else None

    def get_handlers(self, tool_name: str) -> list[ToolHandler]:
        """Return ALL handlers for *tool_name* in priority order."""
        return [h for _, h in self._handlers.get(tool_name, [])]

    # ── Frontend discovery ──────────────────────────────────────────────

    def list_plugins(self) -> list[dict[str, Any]]:
        """Return metadata for all registered plugins (for frontend display)."""
        return [
            {k: v for k, v in info.items() if not k.startswith("_")}
            for info in self._plugin_infos.values()
        ]

    def get_plugin_info(self, tool_name: str) -> dict[str, Any] | None:
        """Return plugin metadata for a specific tool name."""
        info = self._plugin_infos.get(tool_name)
        if info:
            return {k: v for k, v in info.items() if not k.startswith("_")}
        return None

    def tool_names(self) -> list[str]:
        """Return all tool names that have at least one handler registered."""
        return list(self._handlers.keys())


registry = ToolRegistry()
