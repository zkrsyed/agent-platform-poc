"""What `adk web` does for you, in about 50 lines: SessionService + Runner + events."""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "agents" / "ga4_guide" / ".env")  # adk run/web do this for you
sys.path.insert(0, str(ROOT / "agents"))

from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from ga4_guide.agent import root_agent  # noqa: E402

APP, USER = "ga4_guide", "analyst-1"


async def ask(runner: Runner, session_id: str, text: str) -> None:
    print(f"\n=== YOU: {text}")
    message = types.Content(role="user", parts=[types.Part(text=text)])
    async for event in runner.run_async(user_id=USER, session_id=session_id, new_message=message):
        for part in event.content.parts if event.content and event.content.parts else []:
            if part.function_call:
                print(f"  [{event.author}] calls tool {part.function_call.name}({dict(part.function_call.args)})")
            elif part.function_response:
                print(f"  [{event.author}] tool result {part.function_response.response}")
            elif part.text:
                print(f"  [{event.author}] says: {part.text.strip()}")
        if event.actions and event.actions.state_delta:
            print(f"      state change: {event.actions.state_delta}")


async def main() -> None:
    # Tracing to Langfuse is switched on by agents/ga4_guide/__init__.py when the agent is imported.
    sessions = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name=APP, session_service=sessions)

    first = await sessions.create_session(app_name=APP, user_id=USER)
    await ask(runner, first.id, "Hi, I'm Priya from the merch analytics team.")
    await ask(runner, first.id, "How many purchases were there in December 2020?")

    first = await sessions.get_session(app_name=APP, user_id=USER, session_id=first.id)
    print(f"\n--- session {first.id[:8]}… has {len(first.events)} events")
    print("--- its state:", first.state)

    second = await sessions.create_session(app_name=APP, user_id=USER)
    print("--- a NEW session for the same user starts with:", second.state)


if __name__ == "__main__":
    asyncio.run(main())