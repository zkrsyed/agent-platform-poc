# Lesson 8: Deploy to Agent Runtime ☁

**Goal:** run `ga4_guide` in Google Cloud instead of on your machine: on **Agent Runtime**, with its own **Agent Identity**. Then ask it a question from a script and see what happens when an agent has an identity but no permissions yet. About 60 minutes, much of it waiting for the deploy.

**This lesson creates a cloud resource.** Steps 1 to 3 are local and free. **Step 4 deploys**: we do it together, only after you've read the plan and said go.

**Cost (docs, not yet verified on a bill):** Agent Runtime bills for the compute an agent uses while it runs. The docs say: "While this feature is in Preview, even if you configure a higher number of minimum instances, you won't be billed for time when an agent is idle", and idle instances "can scale down after 15 minutes". We also set `min_instances` to 0. Plus the usual Gemini and BigQuery calls (cents). The Google pricing page was too big for me to read, so check it in the console before Step 4 (**to check**).

## Why this lesson exists

So far the agent runs only while `adk web` runs on your laptop, as **you** (your login). A real agent runs as a **service**: always reachable, used by other people and other agents, and acting as **itself**, with its own identity and only the permissions it needs. That's what Agent Runtime gives you, and it's the base for the next lessons: permissions (9), the registry (10), the gateway (11) and A2A (12).

## The ideas

| Idea | One line | .NET comparison |
|---|---|---|
| **Agent Runtime** | Google's managed hosting for agents (formerly Vertex AI Agent Engine; the product is now "Gemini Enterprise Agent Platform", **docs**). The API still calls a deployed agent a `reasoningEngines` resource | Azure App Service for agents |
| **`adk deploy agent_engine`** | Packages one agent folder, builds a container, and creates or updates the deployed agent | `dotnet publish` + deploy |
| **Agent Identity** | The deployed agent gets its **own principal**, `principal://agents.global....system.id.goog/resources/aiplatform/projects/NUMBER/locations/REGION/reasoningEngines/ID` (**docs**), instead of borrowing a shared service account | A managed identity |
| **Principal** | Who IAM sees when a call arrives. Locally that's you; deployed, it's the agent | `ClaimsPrincipal` |
| **`.agent_engine_config.json`** | Deploy settings next to the agent: identity type, min and max instances | `appsettings.json` for hosting |
| **`min_instances` / `max_instances`** | How many copies run: 0 to 75 minimum (default **1**), 1 to 1000 maximum (**docs**) | App Service scale-out |

## What's different in the cloud (all verified while preparing this lesson)

1. **Only the agent folder is uploaded.** Our skill lives in `skills/`, outside `agents/ga4_guide/`, so a deployed copy would have no skill. We copy it **into** the deployed folder.
2. **`adk deploy` uploads every value in the agent folder's `.env`** as an environment variable (ADK's deploy code reads it with `dotenv_values`). Our `.env` holds the **Langfuse secret key** and `OTEL_*` lines pointing at `localhost`. So we never deploy `agents/ga4_guide` as it is: we build a clean copy with a new `.env`.
3. **`gemini-3.5-flash` isn't served in `us-central1`.** A test call there returned `404 NOT_FOUND`; on `global` it answered. Agent Runtime runs in a region, and `adk deploy --region` overrides `GOOGLE_CLOUD_LOCATION`. So we pin the model's location in code with ADK's `Gemini(..., client_kwargs={"location": "global"})`.
4. **Langfuse can't see the deployed agent**: it runs on `localhost` on your server. The deployed agent's traces go to Google's Cloud Trace instead (lesson 16).

---

## Step 1. Prepare `ga4_guide` for the cloud (local, free)

Two small edits in **`agents/ga4_guide/agent.py`**.

**a)** Add the import under `from google.adk.agents import Agent`:

```python
from google.adk.models import Gemini
```

**b)** Replace `MODEL = "gemini-3.5-flash"` with:

```python
# Lesson 8: gemini-3.5-flash is served only from the "global" location, but a deployed agent runs in a
# region (us-central1), so we pin the model's location here instead of relying on GOOGLE_CLOUD_LOCATION.
MODEL = Gemini(model="gemini-3.5-flash", client_kwargs={"enterprise": True, "location": "global"})
```

**c)** Replace the `SKILL_DIR = ...` line with:

```python
_HERE = Path(__file__).resolve().parent
# Lesson 8: a deployed copy carries the skill inside its own folder; locally it's in repo_root/skills.
SKILL_DIR = next(
    d for d in (_HERE / "skills" / "ga4-context", _HERE.parents[1] / "skills" / "ga4-context") if d.is_dir()
)
```

Check that nothing broke locally: run `./scripts/adk.sh web agents`, pick **ga4_guide**, and ask one question. It should behave exactly as before.

## Step 2. Build a clean copy to deploy (local, free)

Create **`scripts/stage_deploy.py`**:

```python
"""Build a clean, self-contained copy of ga4_guide to deploy (lesson 8). Changes nothing in the cloud.

  uv run python scripts/stage_deploy.py

It creates build/ga4_guide/ with:
  agent.py, __init__.py          copied from agents/ga4_guide
  skills/ga4-context/            the skill, copied INSIDE the agent folder (only this folder is uploaded)
  .env                           ONLY the Google Cloud settings: no Langfuse key, no OTEL lines
  .agent_engine_config.json      deploy settings: agent identity, scale to zero
"""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "agents" / "ga4_guide"
OUT = ROOT / "build" / "ga4_guide"

shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir(parents=True)
for name in ("agent.py", "__init__.py"):
    shutil.copy2(SRC / name, OUT / name)
shutil.copytree(ROOT / "skills" / "ga4-context", OUT / "skills" / "ga4-context")

# adk deploy uploads EVERY value in the agent folder's .env as an environment variable,
# so we write a new one with only what the deployed agent needs.
(OUT / ".env").write_text(
    "GOOGLE_GENAI_USE_ENTERPRISE=TRUE\n"
    "GOOGLE_CLOUD_PROJECT=kc-okf-poc-261122\n"
    "GOOGLE_CLOUD_LOCATION=us-central1\n"
)

(OUT / ".agent_engine_config.json").write_text(json.dumps({
    "identity_type": "AGENT_IDENTITY",  # the agent gets its own identity (a principal), not a shared service account
    "min_instances": 0,                 # scale to zero when idle (default is 1)
    "max_instances": 1,                 # a POC needs one
}, indent=2) + "\n")

for f in sorted(OUT.rglob("*")):
    if f.is_file():
        print(f.relative_to(ROOT), f.stat().st_size, "bytes")
```

Add the build folder to **`.gitignore`** (it's generated):

```bash
echo "build/" >> .gitignore
```

Run it:

```bash
uv run python scripts/stage_deploy.py
cat build/ga4_guide/.env build/ga4_guide/.agent_engine_config.json
```

**Look for:** 7 files under `build/ga4_guide/`, including `skills/ga4-context/SKILL.md` and its two reference files, a `.env` with only three `GOOGLE_*` lines (**no** `OTEL` and **no** Langfuse key), and the config with `"identity_type": "AGENT_IDENTITY"`.

Optional local check of the built copy, with the region set the way the cloud will set it:

```bash
cd ~/apps/agent-platform-poc && set -a && . build/ga4_guide/.env && set +a && uv run adk run build/ga4_guide
```

Ask `What date range does the table cover?` and quit with `exit`. (**verified** with a small script that runs the built agent the same way: with `GOOGLE_CLOUD_LOCATION=us-central1` it answered "November 1, 2020, to January 31, 2021", thanks to the pinned model location. I haven't tried `adk run` on it.)

## Step 3. A script to talk to the deployed agent

Create **`scripts/runtime.py`**:

```python
"""Look at, talk to, or delete our deployed agent on Agent Runtime (lesson 8).

  uv run python scripts/runtime.py info   RESOURCE          # name, identity, settings
  uv run python scripts/runtime.py ask    RESOURCE "question"
  uv run python scripts/runtime.py delete RESOURCE          # removes the deployed agent

RESOURCE is what `adk deploy` printed: projects/.../locations/us-central1/reasoningEngines/ID
(or just reasoningEngines/ID).
"""

import asyncio
import sys

import agentplatform  # the newer name of the Vertex AI SDK (vertexai.Client is deprecated)

PROJECT = "kc-okf-poc-261122"
REGION = "us-central1"

client = agentplatform.Client(project=PROJECT, location=REGION)


def info(name: str) -> None:
    agent = client.runtimes.get(name=name)
    r = agent.api_resource
    spec = r.spec
    print("name:              ", r.name)
    print("display name:      ", r.display_name)
    print("created / updated: ", r.create_time, "/", r.update_time)
    print("identity type:     ", getattr(spec, "identity_type", None))
    print("runs as:           ", getattr(spec, "effective_identity", None))


async def ask(name: str, question: str) -> None:
    agent = client.runtimes.get(name=name)
    async for event in agent.async_stream_query(user_id="lesson8", message=question):
        author = event.get("author", "?")
        for part in (event.get("content") or {}).get("parts", []):
            if "function_call" in part:
                print(f"[{author}] CALL {part['function_call']['name']}")
            elif "function_response" in part:
                print(f"[{author}] RESULT {str(part['function_response'].get('response'))[:300]}")
            elif part.get("text") and not part.get("thought"):
                print(f"[{author}] {part['text']}")


def delete(name: str) -> None:
    client.runtimes.delete(name=name, force=True)  # force: also delete its sessions
    print("deleted", name)


if __name__ == "__main__":
    command, name = sys.argv[1], sys.argv[2]
    if command == "info":
        info(name)
    elif command == "ask":
        asyncio.run(ask(name, sys.argv[3]))
    elif command == "delete":
        delete(name)
    else:
        sys.exit(__doc__)
```

It uses the `agentplatform` package, the newer name of the Vertex AI SDK (it came with ADK; `vertexai.Client` now prints "deprecated, please use agentplatform.Client", **verified**). `runtimes` is its name for deployed agents. A deployed ADK agent answers `async_stream_query` (**docs**: ADK's deploy code says so); we'll see the event format for real in Step 6.

---

## Step 4. Deploy ☁ (together, after you say go)

Before running it, check two things in the console: the **Agent Runtime pricing** section, and that you're in project `kc-okf-poc-261122`. Then:

```bash
cd ~/apps/agent-platform-poc
uv run adk deploy agent_engine --project kc-okf-poc-261122 --region us-central1 \
  --display_name ga4-guide --description "GA4 data guide (lesson 8)" build/ga4_guide
```

What it does (from ADK's deploy code, **verified**): reads `.env` and `.agent_engine_config.json`, writes a Dockerfile, **creates a new Agent Runtime instance**, uploads the folder, and builds and starts the container. If the update fails, it deletes the instance it just created.

**Look for:** `Created a new instance: projects/.../reasoningEngines/ID`, then `Deployed to Agent Platform: projects/.../reasoningEngines/ID`. **Copy that resource name**: every later step needs it. It may take several minutes. If it asks to enable an API (for example Cloud Build), stop and tell me before saying yes.

## Step 5. Look at what was created

```bash
uv run python scripts/runtime.py info projects/.../reasoningEngines/ID
```

**Look for:** `identity type: AGENT_IDENTITY` and `runs as:` a long `agents.global....system.id.goog/...` name. That's the agent's own identity. Also open **Agent Platform → Agent Runtime** in the console and find `ga4-guide`.

## Step 6. Ask it a question, and expect trouble

```bash
uv run python scripts/runtime.py ask projects/.../reasoningEngines/ID "What was net merch revenue for December 2020?"
```

**What I expect (guess):** the model answers, because agent identities come with default roles for the platform (**docs**: `roles/aiplatform.agentDefaultAccess`). But **`execute_sql` and the catalog calls fail with 403**, because the agent's identity has **no** BigQuery or Knowledge Catalog permissions yet. Locally those calls worked because they ran as **you**.

That 403 is the point of the lesson. The agent now acts as itself, and it can do only what it's been allowed to do. Lesson 9 grants exactly the roles it needs (least privilege) and checks again.

## Step 7. Keep it or delete it

For lessons 9 to 12 we want this agent deployed, so the plan is to **keep it**: idle time isn't billed while the scaling feature is in Preview (**docs**), and `min_instances` is 0. If you'd rather not keep it running:

```bash
uv run python scripts/runtime.py delete projects/.../reasoningEngines/ID
```

## Step 8. Commit

```bash
git status --short
git add .gitignore agents/ga4_guide/agent.py scripts/stage_deploy.py scripts/runtime.py && git commit -m "Lesson 8: deploy ga4_guide to Agent Runtime with agent identity"
```

`build/` stays out of git. Don't commit the resource name with your project number in it if you share the repo; it's fine in your own notes.

## Check yourself

1. Why can't we deploy `agents/ga4_guide` folder as it is?
2. Why did the model need `location: "global"` in code, and what would happen without it?
3. Locally the agent could run SQL; deployed it gets a 403. What changed?
4. What is the agent's principal, and how is it different from a service account?
5. What do `min_instances: 0` and `max_instances: 1` do?

## Send me back

- The resource name `adk deploy` printed (you can blank out the project number)
- The output of `runtime.py info`
- The output of `runtime.py ask`, especially any 403
- How long the deploy took, and anything that didn't match this page

Next, lesson 9: **identity, IAM and guardrails in code**: grant the agent's principal only the roles it needs, then add an ADK plugin that logs every tool call and asks before risky ones.
