"""Lesson 23: two plugins that cut the tokens ga4_guide sends to Gemini.

Every Gemini call re-sends the whole conversation, tool results included. One question made
7 Gemini calls (lesson 11's trace), so a big tool result is paid for again and again.

  TrimMcpPlugin   MCP tools return their result twice: `content` (text) and `structuredContent`
                  (the same data as JSON). Lesson 4 measured ~36,700 characters each for
                  `lookup_context`. Keep one copy.
  ToolCachePlugin The same catalog call with the same arguments in the same session returns the
                  answer saved in session state, without calling the catalog again.

Both are switched on in agent.py by environment variables, so we can measure before and after.

ADK runs plugin callbacks in list order and STOPS at the first one that returns something
("early exit", plugins/plugin_manager.py). So ToolCachePlugin goes first and returns None after
saving; TrimMcpPlugin goes last and returns the trimmed result.
"""

import json
from typing import Any, Optional

from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

# Read-only catalog tools whose answers don't change during a conversation.
CACHEABLE = {"search_entries", "lookup_context", "lookup_entry"}


def trim(result: Any) -> Any:
    """The same result without `structuredContent`, when `content` already has it as text."""
    if isinstance(result, dict) and "structuredContent" in result and result.get("content"):
        return {k: v for k, v in result.items() if k != "structuredContent"}
    return result


class TrimMcpPlugin(BasePlugin):
    """Drops `structuredContent` when the same result is already in `content` as text."""

    def __init__(self) -> None:
        super().__init__(name="trim_mcp")

    async def after_tool_callback(
        self, *, tool: BaseTool, tool_args: dict[str, Any], tool_context: ToolContext, result: dict
    ) -> Optional[dict]:
        trimmed = trim(result)
        return trimmed if trimmed is not result else None  # a dict replaces what the model sees


class ToolCachePlugin(BasePlugin):
    """Answers repeated catalog calls from session state instead of calling the catalog again."""

    def __init__(self) -> None:
        super().__init__(name="tool_cache")

    @staticmethod
    def _key(tool: BaseTool, tool_args: dict[str, Any]) -> str:
        # Same tool + same arguments = same key. `sort_keys` so argument order doesn't matter.
        return "cache:" + tool.name + ":" + json.dumps(tool_args, sort_keys=True)

    async def before_tool_callback(
        self, *, tool: BaseTool, tool_args: dict[str, Any], tool_context: ToolContext
    ) -> Optional[dict]:
        if tool.name not in CACHEABLE:
            return None
        cached = tool_context.state.get(self._key(tool, tool_args))
        if cached is not None:
            print(f"[tool_cache] HIT {tool.name}")
            return cached  # returning a dict skips the real call
        return None

    async def after_tool_callback(
        self, *, tool: BaseTool, tool_args: dict[str, Any], tool_context: ToolContext, result: dict
    ) -> Optional[dict]:
        if tool.name in CACHEABLE and isinstance(result, dict) and not result.get("isError"):
            tool_context.state[self._key(tool, tool_args)] = trim(result)  # saved with the session
        return None  # let the next plugin (trim) run
