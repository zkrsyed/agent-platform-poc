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

> Where did the sessions go? Into **`agents/ga4_guide/.adk/session.db`**, a SQLite file (**verified**). It's git-ignored. Its tables show state scoping as real storage:
>
> | Table | Holds | State prefix |
> |---|---|---|
> | `sessions` | One row per conversation; `state` column = session keys (`last_answer`, `times_remembered`) | none |
> | `user_states` | One row per **user_id**; the `user:` keys, stored *without* the prefix | `user:` |
> | `app_states` | One row per app | `app:` |
> | `events` | Every event, as JSON in `event_data` | – |
>
> `adk run` and `adk web` use **different user IDs** (`test_user` vs `user` in our run, **verified**). That's why the name you gave in the terminal wasn't known in the web UI. On Agent Runtime the managed **Sessions** service replaces this file (lesson 8).

## Step 4b. Look inside the session database yourself

**SQLite** is a whole database in one file. It has no server, it's public domain, and it ships with Python, every phone and every browser. (.NET comparison: SQL Server LocalDB, only lighter; use it from C# with `Microsoft.Data.Sqlite`.) Because it's a file, everything survives a restart. Stop `adk web`, start it again, and the data is still there.

Install the command-line shell once (Ubuntu):

```bash
sudo apt install sqlite3
```

Open the file **read-only**, so you can't change it by accident, even while `adk web` is running:

```bash
sqlite3 -readonly -box agents/ga4_guide/.adk/session.db
```

Then run these inside the `sqlite>` prompt:

```sql
.tables
SELECT app_name, user_id, state FROM user_states;
SELECT user_id, id, state FROM sessions;
```

The whole conversation, one row per event. `author` and the content live **inside** the `event_data` JSON, so `json_extract` pulls them out:

```sql
SELECT user_id,
       json_extract(event_data, '$.author') AS author,
       substr(coalesce(json_extract(event_data, '$.content.parts[0].text'),
                       'calls '     || json_extract(event_data, '$.content.parts[0].function_call.name'),
                       'result of ' || json_extract(event_data, '$.content.parts[0].function_response.name')), 1, 45) AS what,
       substr(json_extract(event_data, '$.actions.state_delta'), 1, 70) AS state_change
FROM events ORDER BY timestamp;
```

Type `.quit` to leave.

**What we saw (verified, 2026-11-25):**

| Query | What it showed | The idea behind it |
|---|---|---|
| `user_states` | Two rows, `test_user` (from `adk run`) and `user` (from `adk web`), each `{"analyst_name": …, "team": …}`, **without** the `user:` prefix | `user:` state is stored once per app + user, so every session of that user sees it |
| `sessions` | One row per conversation; `state` holds `last_answer` and `times_remembered`. `adk web` also adds `__session_metadata__: {"displayName": "hi"}`, the session's name in the UI, taken from the first message | State with no prefix belongs to one conversation |
| `events` | 8 rows per conversation: user text → model text → user text → **calls** `remember_analyst` → **result of** `remember_analyst` → model text → … | `adk web`'s Events tab is just this table |
| `events.state_change` | The `user:` keys and `times_remembered` change on the **tool result** event; `last_answer` changes on **every** model text event | Changes to state are recorded as events. Replaying the events rebuilds the state |
| The two `last_answer`s | Two runs, two different SQL guesses: one filtered on `event_date`, the other used `_TABLE_SUFFIX` (wrong: the table is partitioned, not sharded) | Without the catalog the model **guesses** the schema. Lesson 3 fixes that |

The `events` table also has `session_id` and a **foreign key to `sessions` with `ON DELETE CASCADE`**: delete a session and its events go with it. Each event's JSON also records `model_version` (`gemini-3.5-flash`) and an `invocation_id` that groups all the events of one turn.

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

## Step 5b. Watch the same run in Langfuse

The script prints events as text. **Langfuse** shows the same run as a picture: a tree of **spans** (one per agent step, model call and tool call) with inputs, outputs, tokens and timings. Lesson 16 does this properly for the deployed agents. Here we only point the local agent at your own Langfuse.

How it works (**verified** in ADK 2.15's `google/adk/telemetry/setup.py`): ADK already creates OpenTelemetry spans. If the standard `OTEL_EXPORTER_OTLP_*` environment variables are set, `maybe_set_otel_providers()` sends them to that address. Langfuse accepts OpenTelemetry at `/api/public/otel` (**docs**; on this server `…/v1/traces` answers `401` without keys, so the endpoint exists, **verified**). Nothing new to install.

| Idea | One line | .NET comparison |
|---|---|---|
| **Span** | One timed step with a start, end and attributes | One dependency call in Application Insights |
| **Trace** | All spans of one request, as a tree | One end-to-end transaction |
| **OpenTelemetry (OTel)** | The open standard for creating and sending spans | `System.Diagnostics.Activity` + OTel exporter |
| **OTLP endpoint** | The address that receives the spans | The Application Insights connection string |

**1. Get keys.** Open Langfuse (`http://localhost:3000` on the server; from another computer, use the same SSH tunnel as Step 4 with `-L 3000:localhost:3000`). Create a project called `agent-platform-poc`, then **Settings → API Keys → Create**. Copy the public key (`pk-lf-…`) and the secret key (`sk-lf-…`).

**2. Turn the two keys into one login string** (put your keys in, keep the colon):

```bash
echo -n "pk-lf-XXXX:sk-lf-XXXX" | base64 -w0; echo
```

**3. Add three lines to `agents/ga4_guide/.env`** (git-ignored, so the keys stay private). Paste the output of step 2 after `Basic%20`:

```
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:3000/api/public/otel/v1/traces
OTEL_EXPORTER_OTLP_TRACES_HEADERS=Authorization=Basic%20PASTE_HERE
OTEL_SERVICE_NAME=ga4_guide
```

- We set only the **TRACES** address, not the general `OTEL_EXPORTER_OTLP_ENDPOINT`, because Langfuse takes traces, not metrics or logs (**docs**).
- `%20` is a space. The OTel spec wants it written like that in this variable.

**4. Switch tracing on in the script.** In `scripts/runner_demo.py`, add this import next to the other ADK imports:

```python
from google.adk.telemetry.setup import maybe_set_otel_providers  # noqa: E402
```

and make this the first line inside `main()`:

```python
    maybe_set_otel_providers()  # sends spans to the OTEL_EXPORTER_OTLP_* address in .env, if set
```

**5. Run it again:**

```bash
uv run python scripts/runner_demo.py
```

Then open Langfuse → your project → **Tracing**. What we **verified** (2026-11-25):
- **Two traces**, one per message, named `invoke_workflow ga4_guide`. Both carry the ADK session ID as `gen_ai.conversation.id`, so Langfuse groups them as one **session**.
- Inside turn 1: `invoke_agent ga4_guide` → `generate_content gemini-3.5-flash` → **`remember_analyst`** (a TOOL span, 2 ms) → a second `generate_content`. Turn 2 has **no tool span**.
- Per model call: latency, **token counts** (turn 1: 562 + 664 tokens; turn 2: 1,111) and a **cost** (about $0.004 per turn).
- The graph panel draws `__start__ → invoke_workflow → invoke_agent → generate_content → __end__`.
- **Not there by default:** the prompt text, your message and the model's reply. Trace Input/Output show `null`, and each model call's input holds only the tool list. Fix below.

The names say `invoke_workflow` because ADK 2.x runs every agent as a graph **workflow** (**verified** in the span attributes: `gen_ai.operation.name = invoke_workflow`).

### Get the text into Langfuse (verified 2026-11-25)

In ADK 2.15, message content is sent as OpenTelemetry **log events**, and only if a content switch is on. We export only **traces**, and Langfuse takes traces, so the words never arrived. Add two more lines to `agents/ga4_guide/.env`:

```
OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=SPAN_ONLY
```

- The first selects ADK's newer span format. The second puts the message text **on the spans** (`SPAN_ONLY`). No code change.
- Run the script again. In Langfuse, **click the `generate_content` row** (not the top row) and look at Input and Output:
  - 1st model call, input: the system prompt with an **empty name** (`The analyst you are talking to:  (team: )`); output: a call to `remember_analyst`.
  - the tool row: its arguments and its result.
  - 2nd model call, input: the **same prompt, now filled in** (`Priya (team: merch analytics)`). That's the `{user:analyst_name?}` placeholder refreshed from state on every call.
- The top rows (`invoke_workflow`, `invoke_agent`) and the trace's own Input/Output stay `null`. The content lives on the model and tool rows.
- Compare with the `langfuse` SDK way (three `LANGFUSE_*` variables plus an import). It captures text by itself. Ours needs no new package but needs these two settings.

**`adk web` too:** `adk web` sets up the same exporter by itself when the variables are set (**verified** in `google/adk/cli/api_server.py`). Load the `.env` into the shell first, so they are there when it starts:

```bash
set -a && source agents/ga4_guide/.env && set +a && uv run adk web agents
```

> Once message content is switched on, prompts and replies leave your process. That's fine for a private Langfuse; for a shared or production backend, think about whether they may contain personal data.

## Step 6. Commit your work

```bash
git status --short
```

**Look for:** `scripts/runner_demo.py` is listed, and **`.env` is not** (the root `.gitignore` excludes it; it now holds your Langfuse keys too). The agent files were already committed with the plan update.

```bash
git add scripts && git commit -m "Lesson 2: runner demo"
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
