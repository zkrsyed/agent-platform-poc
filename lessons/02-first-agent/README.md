# Lesson 2: Your first ADK agent

**Goal:** build `ga4_guide` with no data access yet. You'll see the parts every ADK agent has (Agent, instruction, tool, Runner, Session, State, Events) and run it three ways: in the terminal, in the web UI, and from your own Python script. About 30–40 minutes.

**Cost:** a few Gemini calls (cents). Nothing is created in GCP.

## The ideas

| Idea | One line | .NET comparison |
|---|---|---|
| **Agent** (`LlmAgent`) | Name + model + instruction + tools. The model decides what to do next | A controller whose actions are chosen at runtime |
| **`root_agent`** | The variable ADK looks for in `agent.py`. It's the entry point | `Program.Main` |
| **Instruction** | The system prompt. `{user:analyst_name?}` is filled from **state**; `?` means "blank if missing" | A Razor template bound to session data |
| **Tool** | A plain Python function. ADK turns its **signature + docstring** into the tool description the model reads | A public method with XML docs (Swagger reads them) |
| **`ToolContext`** | Extra parameter ADK passes to a tool: state, artifacts, memory, credentials. The model never sees it | `HttpContext` injected into an action |
| **Runner** | The engine: takes your message, calls the model, runs tools, records events | The ASP.NET request pipeline |
| **Session** | One conversation: its list of **events** plus its **state** | A session row in SQL Server |
| **State** | Key-value data. The prefix sets the scope: none = this session, `user:` = all of this user's sessions, `app:` = everyone, `temp:` = this turn only | `Session[...]`, user profile, app cache, `HttpContext.Items` |
| **Event** | One step: user message, model text, tool call, tool result, state change | A row in an audit table |
| **SessionService** | Where sessions are stored. Locally `InMemorySessionService` or SQLite; on Agent Runtime a managed service | `ISessionStore` (memory vs SQL) |

ADK 2.x detail from the installed code (**verified**): the "use Google Cloud, not an API key" switch is now **`GOOGLE_GENAI_USE_ENTERPRISE=1`**. Older docs say `GOOGLE_GENAI_USE_VERTEXAI=TRUE`; the library still reads that, but the new name wins if both are set.

## What you'll have at the end

```
agents/
  ga4_guide/
    __init__.py      ← tells Python (and ADK) this folder is a package
    agent.py         ← root_agent lives here
    .env             ← project / location / backend (git-ignored)
    .gitignore       ← written by adk create
scripts/
  runner_demo.py     ← the Runner by hand, so adk web is no longer magic
```

---

## Step 1. Scaffold with `adk create`

```bash
cd ~/apps/agent-platform-poc && export CLOUDSDK_ACTIVE_CONFIG_NAME=kc-okf
```

```bash
uv run adk create agents/ga4_guide --model gemini-3.5-flash --project kc-okf-poc-261122 --region global --type code
```

Look at what it made:

```bash
ls -la agents/ga4_guide && cat agents/ga4_guide/.env && echo && cat agents/ga4_guide/agent.py
```

**Look for:**
- `.env` holds `GOOGLE_GENAI_USE_ENTERPRISE=1`, `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION=global`. ADK loads it automatically. It searches from the agent folder **upwards** for the first `.env` it finds (**verified** in `google/adk/cli/utils/envs.py`).
- `agent.py` defines `root_agent = Agent(...)` with a one-line instruction and no tools.

> `--region global` is because `gemini-3.5-flash` only answered on `global` in kc-okf. When we deploy in lesson 8, the *agent* runs in a region such as `us-central1`, while the *model* is still called on `global`. Those are two different settings.

## Step 2. Replace `agent.py` with the GA4 guide

Paste this into **`agents/ga4_guide/agent.py`**, replacing everything:

```python
"""ga4_guide, lesson 2 version.

No data or catalog access yet. This version only shows the shape of an ADK agent:
instruction + one tool + state.
"""

from google.adk.agents import Agent
from google.adk.tools import ToolContext

MODEL = "gemini-3.5-flash"


def remember_analyst(name: str, team: str, tool_context: ToolContext) -> dict:
    """Remember who the analyst is, so later answers can address them by name.

    Call this once, as soon as the analyst tells you their name and team.

    Args:
        name: The analyst's first name.
        team: The team the analyst works in.
    """
    # "user:" prefix = kept for this user across ALL their sessions.
    tool_context.state["user:analyst_name"] = name
    tool_context.state["user:team"] = team
    # No prefix = kept only in THIS session.
    tool_context.state["times_remembered"] = tool_context.state.get("times_remembered", 0) + 1
    return {"status": "saved", "name": name, "team": team}


root_agent = Agent(
    name="ga4_guide",
    model=MODEL,
    # The description is for OTHER agents and registries (lessons 10 and 12), not for this model.
    description=(
        "Answers questions about the GA4 sample table "
        "kc-okf-poc-261122.ga4_sample.events (Google Merchandise Store)."
    ),
    instruction="""You are the GA4 data guide for the BigQuery table
`kc-okf-poc-261122.ga4_sample.events` (Google Merchandise Store, 2020-11-01 to 2021-01-31).

The analyst you are talking to: {user:analyst_name?} (team: {user:team?}).
If the name above is empty, ask for their name and team once, then call `remember_analyst`.

Right now you have NO access to the data or the data catalog.
When asked for numbers, say so plainly and say what access you would need. Never invent figures.
Keep answers to a few sentences.""",
    tools=[remember_analyst],
    # Copies the agent's final reply into session state under this key.
    output_key="last_answer",
)
```

`__init__.py` already says `from . import agent as agent`. Leave it as it is.

**Read the code before running it:**
- The model never sees `tool_context`. ADK hides it and fills it in.
- The docstring **is** the tool's documentation for the model. A vague docstring means the tool gets called at the wrong time.
- `{user:analyst_name?}` is filled in again **on every turn** from the latest state.

## Step 3. Chat in the terminal: `adk run`

```bash
uv run adk run agents/ga4_guide
```

Try these three messages, then type `exit`:

1. `hi`. It should ask for your name and team.
2. `I'm Sam from merch analytics`. It should call `remember_analyst`.
3. `How many purchases were there in December 2020?`. It should say it has no data access, not make up a number.

**Look for:** an answer that uses your name in turn 3. That only works because the tool wrote `user:analyst_name` to state and the instruction read it back.

## Step 4. The developer web UI: `adk web`

```bash
uv run adk web agents
```

`agents` is the *folder that contains* agent folders, so every agent you add later shows up in the dropdown.

`adk web` listens on `127.0.0.1:8000`, which means this machine only. If your browser is on another computer, open a tunnel from that computer and then browse to `http://localhost:8000`:

```bash
ssh -L 8000:localhost:8000 zs@homeserver
```

(Or run `adk web agents --host 0.0.0.0` on a network you trust. It has no login.)

In the UI, pick **ga4_guide** and repeat the three messages. Then explore:

| Tab / panel | What to look at | Idea it shows |
|---|---|---|
| **Events** | Click each row: user message → `functionCall remember_analyst` → `functionResponse` → model text | Events |
| **State** | `user:analyst_name`, `user:team`, `times_remembered`, `last_answer` | State and its prefixes |
| **Sessions** | Start a **new session**, say `hi`, and check whether it already knows your name | `user:` state outlives one session |
| **Trace** | Timing bars for the model call and the tool call | Spans (lesson 16 shows the same in Cloud Trace) |
| The graph icon, if present | Agent → tool diagram | A local version of Topology |

Stop it with `Ctrl+C`.

> Where did the sessions go? `adk web` stores them locally (**guess**: under `.adk/` in SQLite). That folder is git-ignored. On Agent Runtime the managed **Sessions** service replaces it (lesson 8).

## Step 5. Do it yourself: the Runner by hand

`adk run` and `adk web` are both thin wrappers around a **Runner** and a **SessionService**. Writing those yourself removes the magic. In lesson 6 (eval) and lesson 8 (deploy), ADK does exactly this.

Create **`scripts/runner_demo.py`**:

```python
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
```

```bash
uv run python scripts/runner_demo.py
```

**Look for:**
- Turn 1: a `calls tool remember_analyst(...)` line, then `tool result`, then a `state change` line showing the `user:` keys.
- Turn 2: no tool call. It explains that it has no data access.
- The **new** session starts with `user:analyst_name` and `user:team` but **not** `times_remembered` or `last_answer`. That is state scoping in action (**verified** with an offline test against ADK 2.15 before writing this lesson).
- `InMemorySessionService` forgets everything when the script ends. Run it twice and see.

## Step 6. Commit your work

```bash
git status --short
```

**Look for:** `agents/ga4_guide/agent.py`, `__init__.py`, `.gitignore` and `scripts/runner_demo.py` are listed, and **`.env` is not** (the root `.gitignore` excludes it).

```bash
git add agents scripts && git commit -m "Lesson 2: first ADK agent (ga4_guide) and runner demo"
```

---

## Check yourself

1. Where does the model learn what `remember_analyst` does, and why doesn't it see `tool_context`?
2. You start a new session. Which of these survive: `user:team`, `times_remembered`, `last_answer`? Why?
3. What do `adk run`, `adk web` and your `runner_demo.py` have in common?
4. Why is `description` there if this agent's own model never reads it?

## Send me back

- The output of `runner_demo.py`
- A screenshot of the `adk web` **Events** or **Trace** view (optional, for the record)
- Anything that didn't match this page, especially any tab names in `adk web` that differ

Next, lesson 3: give the agent real tools, the **Knowledge Catalog remote MCP server** and **BigQuery**.
