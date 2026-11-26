"""Guardrails in code (lesson 9): an ADK plugin that runs around EVERY tool call of the agent.

The skill (lesson 4) *asks* the model to follow the rules. This plugin *enforces* some of them,
whatever the model decides:

  1. Log every tool call (name and arguments) and every tool error.
  2. Block SQL that isn't read-only, or that shows city or metro level data (privacy tier C3).
  3. Ask a human before a query that skips the partition filter `event_date_dt` (a full scan).
  4. Stop after 3 failed tool calls in one turn, instead of retrying forever (lesson 8 saw 8).
"""

import asyncio
import logging
import re

from google.adk.plugins import BasePlugin

log = logging.getLogger("ga4_guardrails")

MAX_TOOL_ERRORS = 3
WRITE_WORDS = re.compile(r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|DROP|ALTER|TRUNCATE|GRANT|REVOKE)\b", re.I)
CITY_FIELDS = re.compile(r"\bgeo\.(city|metro)\b", re.I)


def _failed(result) -> bool:
    """Both kinds of tool failure we saw in lesson 8: {'status': 'ERROR'} and {'error': ...}."""
    return isinstance(result, dict) and (result.get("status") == "ERROR" or "error" in result)


class GuardrailsPlugin(BasePlugin):
    def __init__(self) -> None:
        super().__init__(name="ga4_guardrails")

    async def before_tool_callback(self, *, tool, tool_args, tool_context):
        log.info("tool call: %s %s", tool.name, tool_args)

        # 4. Too many failures in this turn: stop calling tools. ("temp:" state lasts one turn.)
        if tool_context.state.get("temp:tool_errors", 0) >= MAX_TOOL_ERRORS:
            log.warning("blocked %s: %d tool errors already", tool.name, MAX_TOOL_ERRORS)
            return {"status": "BLOCKED", "reason": f"{MAX_TOOL_ERRORS} tool calls already failed in this "
                    "turn. Stop calling tools and tell the analyst what failed."}

        if tool.name != "execute_sql":
            return None  # None = let the call run
        sql = tool_args.get("query", "")

        # 2. Hard rules: returning a dict skips the tool; the model gets our dict as the result.
        if WRITE_WORDS.search(sql):
            log.warning("blocked execute_sql: not read-only")
            return {"status": "BLOCKED", "reason": "Only read-only SELECT queries are allowed."}
        if CITY_FIELDS.search(sql):
            log.warning("blocked execute_sql: geo.city / geo.metro")
            return {"status": "BLOCKED", "reason": "geo.city and geo.metro are privacy tier C3. "
                    "Roll up to geo.region or geo.country."}

        # 3. Human in the loop: no partition filter -> ask before running.
        if "event_date_dt" not in sql:
            confirmation = tool_context.tool_confirmation
            if confirmation is None:
                tool_context.request_confirmation(
                    hint="This query has no event_date_dt filter, so it scans the whole table. Run it anyway?",
                    payload={"query": sql},
                )
                tool_context.actions.skip_summarization = True  # wait for the human; don't let the model carry on
                return {"status": "WAITING", "reason": "Asked the analyst to approve a full-table scan."}
            if not confirmation.confirmed:
                return {"status": "BLOCKED", "reason": "The analyst rejected the full-table scan. "
                        "Add an event_date_dt filter."}
        return None

    async def after_tool_callback(self, *, tool, tool_args, tool_context, result):
        if _failed(result):
            errors = tool_context.state.get("temp:tool_errors", 0) + 1
            tool_context.state["temp:tool_errors"] = errors
            log.warning("tool error %d/%d in %s: %s", errors, MAX_TOOL_ERRORS, tool.name, str(result)[:200])
        return None  # None = keep the result as it is

    async def on_tool_error_callback(self, *, tool, tool_args, tool_context, error):
        """A tool that raises (instead of returning an error dict) counts too."""
        if isinstance(error, asyncio.CancelledError):
            return None  # a cancelled call is not a failure
        errors = tool_context.state.get("temp:tool_errors", 0) + 1
        tool_context.state["temp:tool_errors"] = errors
        log.warning("tool exception %d/%d in %s: %s", errors, MAX_TOOL_ERRORS, tool.name, error)
        return None  # None = let ADK handle the error as usual
