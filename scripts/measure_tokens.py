"""Lesson 23: ask ga4_guide two questions in ONE session and count the tokens Gemini was sent.

  uv run python scripts/measure_tokens.py                         # baseline (all cost switches off)
  COST_TRIM=1 uv run python scripts/measure_tokens.py             # + drop the duplicate MCP payload
  COST_TRIM=1 COST_TOOL_CACHE=1 uv run python scripts/measure_tokens.py
  COST_TRIM=1 COST_TOOL_CACHE=1 COST_CONTEXT_CACHE=1 uv run python scripts/measure_tokens.py

Each run calls Gemini for real: roughly $0.10-0.25 (guess, from lesson 11's ~$0.11 per question).
The numbers come from Gemini's own usage report on each response (usage_metadata).
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "agents" / "ga4_guide" / ".env")
sys.path.insert(0, str(ROOT / "agents"))

from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from ga4_guide.agent import app  # noqa: E402

USER = "analyst-1"
QUESTIONS = [
    # The name and team go first so the agent doesn't stop to ask for them.
    "I'm Priya from merch analytics. Why must daily revenue leave out the last 3 days? "
    "Check the catalog entry for the events table.",
    "Which columns in that table hold purchase revenue and refunds? Check the catalog entry again.",
]


async def ask(runner: Runner, session_id: str, text: str) -> dict:
    totals = {"gemini_calls": 0, "input": 0, "cached": 0, "output": 0, "thinking": 0, "tools": []}
    message = types.Content(role="user", parts=[types.Part(text=text)])
    async for event in runner.run_async(user_id=USER, session_id=session_id, new_message=message):
        usage = event.usage_metadata
        if usage and usage.prompt_token_count:
            totals["gemini_calls"] += 1
            totals["input"] += usage.prompt_token_count or 0
            totals["cached"] += usage.cached_content_token_count or 0
            totals["output"] += usage.candidates_token_count or 0
            totals["thinking"] += usage.thoughts_token_count or 0
        for part in event.content.parts if event.content and event.content.parts else []:
            if part.function_call:
                totals["tools"].append(part.function_call.name)
    return totals


async def main() -> None:
    switches = [n for n in ("COST_TRIM", "COST_TOOL_CACHE", "COST_CONTEXT_CACHE") if os.environ.get(n) == "1"]
    print("cost switches on:", ", ".join(switches) or "none (baseline)")
    print("plugins:", [p.name for p in app.plugins], "| context cache:", bool(app.context_cache_config))

    sessions = InMemorySessionService()
    runner = Runner(app=app, session_service=sessions)
    session = await sessions.create_session(app_name=app.name, user_id=USER)

    grand = {"gemini_calls": 0, "input": 0, "cached": 0, "output": 0, "thinking": 0}
    for n, question in enumerate(QUESTIONS, 1):
        t = await ask(runner, session.id, question)
        print(f"\nQ{n}: {t['gemini_calls']} Gemini calls | input {t['input']:,} (cached {t['cached']:,}) "
              f"| output {t['output']:,} | thinking {t['thinking']:,}")
        print(f"    tools: {', '.join(t['tools'])}")
        for k in grand:
            grand[k] += t[k]

    print(f"\nTOTAL: {grand['gemini_calls']} Gemini calls | input {grand['input']:,} "
          f"(cached {grand['cached']:,}, {100 * grand['cached'] / max(grand['input'], 1):.0f}%) "
          f"| output {grand['output']:,} | thinking {grand['thinking']:,}")


if __name__ == "__main__":
    asyncio.run(main())
