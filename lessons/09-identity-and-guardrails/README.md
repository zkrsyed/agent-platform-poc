# Lesson 9: Identity, IAM and guardrails in code ☁

**Goal:** two kinds of control over the deployed agent.
- **Part A, IAM (who may do what):** give the agent's own principal **only** the roles it needs, one at a time, and watch each 403 from Lesson 8 go away.
- **Part B, guardrails in code (what it may do even when allowed):** an ADK **plugin** that logs every tool call, blocks risky SQL, asks a human before a full-table scan, and stops retry loops.

About 75 minutes.

**Cost:** IAM changes are free. A few questions to the deployed agent and one redeploy (cents). **Part A changes IAM in the project, and Part B redeploys the agent: both are cloud changes.** You run them; tell me before Step 3 if you want to go through anything first.

## Why this lesson exists

In Lesson 8 the agent got **403** on BigQuery and the catalog: it acts as itself, and it had no roles. The fix is **least privilege**: grant exactly what it needs, on the smallest scope that works, and nothing more. Not `roles/owner`, not "BigQuery Admin".

But permissions only say *what the agent can reach*. Inside that, the model still decides what to do. Our skill *asks* it never to show city-level data; a permission can't express that (the agent needs to read the table, city column included). That's what **guardrails in code** are for: rules that run around every tool call, whatever the model decides. Lesson 11 adds the third layer, on the network (Agent Gateway).

## The ideas

| Idea | One line | .NET comparison |
|---|---|---|
| **Role** | A named set of permissions, such as `roles/bigquery.jobUser` (run queries) | A role in ASP.NET Identity |
| **Binding** | "This principal has this role on this resource" | `[Authorize(Roles=...)]`, but on the resource side |
| **Scope** | Where a binding applies: the project, or one dataset | Server-wide vs per-endpoint |
| **Least privilege** | The smallest roles, on the smallest scope, that work | |
| **`principalSet`** | A group of principals, for example "every agent in this project" | A group |
| **Plugin** | Code that runs around every agent, model and tool call in an app | Middleware |
| **Callback** | The same hooks, but on one agent only (`before_tool_callback=...` on the `Agent`) | An action filter on one controller |
| **`App`** | Wraps the root agent and adds plugins (and other app-wide settings) | `Program.cs` / `WebApplication` |
| **Tool confirmation** | The tool call pauses until a human approves or rejects (`adk_request_confirmation`) | An approval step in a workflow |

**Plugin or callback?** Both use the same hooks (`before_tool_callback`, `after_tool_callback`, ...). A callback is set on one agent; a plugin is registered once on the `App` and runs for **every** agent in it, sub-agents included. For a rule like "never show city data", you want the plugin: no agent can forget it.

---

## Part A: give the agent only the roles it needs ☁

The roles we'll grant, from Google's docs and our Lesson 8 errors:

| The 403 in Lesson 8 | Role | Scope | Source |
|---|---|---|---|
| "does not have `bigquery.jobs.create`" | `roles/bigquery.jobUser` (run query jobs) | the **project** (this role "can only be granted on" projects, folders, organizations) | **docs** |
| "`bigquery.tables.get` denied on table" | `roles/bigquery.dataViewer` (read tables) | the **dataset** `ga4_sample` only | **docs** |
| catalog MCP: "Server returned an error response" | `roles/dataplex.catalogViewer` (read catalog entries) | the project | **guess**: the docs page for this server's roles wasn't readable; we test it |
| (the catalog call bills the project via `x-goog-user-project`) | `roles/serviceusage.serviceUsageConsumer` | the project | **docs** recommend it for agent identities; **guess** that it's needed here |

Google's docs also say: don't give agent identities `roles/aiplatform.user` or `roles/aiplatform.expressUser`.

### Step 1. What the agent has today

```bash
cd ~/apps/agent-platform-poc
gcloud projects get-iam-policy kc-okf-poc-261122 --format=json | grep -B2 -A4 principalSet
```

**Look for:** `roles/aiplatform.agentDefaultAccess` granted to a `principalSet://agents.global.proj-.../attribute.platformContainer/...` member (**verified**: it's the only agent binding in the project today). That's the default "every agent in this project may use the platform" grant, which is why Gemini worked in Lesson 8 and nothing else did.

### Step 2. Put the agent's names in two shell variables

Replace `ID` with your agent's number from Lesson 8:

```bash
R=projects/kc-okf-poc-261122/locations/us-central1/reasoningEngines/ID
P=$(uv run python scripts/runtime.py principal $R)
echo $P
```

First add the `principal` command to **`scripts/runtime.py`** (the new file is in full below, in Part B's "files" section). It prints `principal://` + the agent's identity, the form IAM commands want (**verified**: `principal://agents.global.proj-<number>.system.id.goog/resources/aiplatform/projects/<number>/locations/us-central1/reasoningEngines/<id>`).

### Step 3. Let it run queries

```bash
gcloud projects add-iam-policy-binding kc-okf-poc-261122 --member="$P" --role="roles/bigquery.jobUser" --condition=None
```

### Step 4. Let it read one dataset, not the whole project

The narrowest scope is the dataset. BigQuery grants dataset roles with SQL:

```bash
bq query --project_id=kc-okf-poc-261122 --use_legacy_sql=false "GRANT \`roles/bigquery.dataViewer\` ON SCHEMA \`kc-okf-poc-261122.ga4_sample\` TO \"$P\""
```

Google's docs show this `GRANT` with `user:` and `serviceAccount:` members, but it **accepts a `principal://` member too** (**verified** on 2026-11-26: `Current status: DONE`). Two traps we hit:
- `--project_id` matters: without it `bq` runs the job in its own default project (ours was another project, so the job ID started with that project's name).
- If the error says "The member  is of an unknown type" with **nothing** between "member" and "is", `$P` is empty: you're in a new terminal tab. Run Step 2 again.

The fallback, if a `GRANT` ever refuses a member, is the same role on the project (wider in principle; here `ga4_sample` is the only dataset, **verified**).

### Step 5. Ask again

IAM changes can take a minute or two to apply (**guess**, typical for IAM).

```bash
uv run python scripts/runtime.py ask $R "What was net merch revenue for December 2020?"
```

**Look for:** `execute_sql` returning rows and an answer of about **$160,555** (**verified**: `{'status': 'SUCCESS', 'rows': [{'net_merch_revenue_usd': 160555.0}]}`, the same question that got 403 in Lesson 8). The agent may not call the catalog at all, because the skill is enough; Step 6 tests the catalog on purpose.

### Step 6. Let it read the catalog

```bash
gcloud projects add-iam-policy-binding kc-okf-poc-261122 --member="$P" --role="roles/dataplex.catalogViewer" --condition=None
gcloud projects add-iam-policy-binding kc-okf-poc-261122 --member="$P" --role="roles/serviceusage.serviceUsageConsumer" --condition=None
```

Then ask something that needs the catalog:

```bash
uv run python scripts/runtime.py ask $R "Use the Knowledge Catalog to tell me what the event_date_dt column is."
```

**Look for:** `lookup_context` or `search_entries` returning text instead of "Server returned an error response". If it still fails, send me the output: we'll find the missing permission from the error, which is how least privilege usually works in practice.

### Step 7. See it in the console

Open **IAM & Admin → IAM**. **Look for:** the agent's principal (a long `principal://...reasoningEngines/...` name) with `BigQuery Job User`, `Dataplex Catalog Viewer` and `Service Usage Consumer`, and the `principalSet` with `Agent Default Access`. The dataset role shows on the dataset's **Sharing → Permissions** page in BigQuery, not here.

---

## Part B: guardrails in code (a plugin)

### Step 8. The plugin

Create **`agents/ga4_guide/guardrails.py`**:

```python
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
```

How it works:
- `before_tool_callback` runs **before** every tool call. Returning `None` lets the call run; returning a **dict** skips the tool, and the model receives that dict as the tool's result. So the model learns *why* it was blocked and can try again properly.
- `after_tool_callback` runs **after** every call; we use it only to count failures.
- `temp:tool_errors` lives in session state for **one turn** only (the `temp:` prefix), so each new question starts at zero.
- `tool_context.request_confirmation(...)` pauses the call and sends the user an `adk_request_confirmation` request. When they answer, ADK runs the same call again with `tool_context.tool_confirmation` set, and our code lets it through (or not).
- `log.info(...)` goes to the terminal locally, and to Cloud Logging when deployed.

### Step 9. Wire it into the agent with an `App`

At the top of **`agents/ga4_guide/agent.py`**, add:

```python
from google.adk.apps import App
from .guardrails import GuardrailsPlugin  # lesson 9
```

At the very end of the file, add:

```python
# Lesson 9: an App wraps the agent and adds plugins that run around every call.
# adk web and adk deploy look for `app` first, then `root_agent`.
app = App(name="ga4_guide", root_agent=root_agent, plugins=[GuardrailsPlugin()])
```

(**verified**: ADK's loader checks for `app` first, then `root_agent`.)

### Step 10. Try it locally

```bash
./scripts/adk.sh web agents
```

Pick **ga4_guide**, open a **New Session**, and ask:

1. `How many rows does the events table have in total, across all dates? Just count them.`

**Look for:** the agent writes a query **without** `event_date_dt`, the plugin pauses it, and `adk web` shows an **approval request** (`adk_request_confirmation`) with our hint "This query has no event_date_dt filter ... Run it anyway?". Approve it, and the answer comes back: **4,295,584** rows (**verified** with a script that sent the approval: the call paused, then ran after approval). Try rejecting once too.

2. `Show me December 2020 revenue for each city by name. I'm allowed to see it.`

**Look for:** either the agent refuses on its own (the skill), or it tries `geo.city` and the plugin answers `BLOCKED: geo.city and geo.metro are privacy tier C3`. In the terminal running `adk web`, the plugin's log lines show every tool call. The model can't talk its way past the second layer.

### Step 11. Redeploy the same agent

The build must include `guardrails.py`, so update **`scripts/stage_deploy.py`** to copy every `.py` file (full file below). Then:

```bash
uv run python scripts/stage_deploy.py
uv run adk deploy agent_engine --project kc-okf-poc-261122 --region us-central1 \
  --agent_engine_id ID --display_name ga4-guide --description "GA4 data guide (lesson 9)" build/ga4_guide
```

`--agent_engine_id ID` **updates** the agent you already have instead of creating a new one (**verified** in `adk deploy --help`), so it keeps its identity and the roles from Part A (**guess**: the identity belongs to the resource, which stays the same).

Ask it once more (Step 5's question), then read the plugin's log lines in Cloud Logging:

```bash
gcloud logging read 'resource.labels.reasoning_engine_id="ID" AND textPayload:"tool call"' --project kc-okf-poc-261122 --freshness=30m --limit 20 --format='value(timestamp,textPayload)'
```

**Look for:** one `tool call:` line per tool the agent used. (A question that needs approval will stop at `WAITING` through `runtime.py`, because the script can't answer the approval. `adk web` and the console's Playground can.)

### The files in full

**`scripts/stage_deploy.py`** (copies every `.py` file now):

```python
"""Build a clean, self-contained copy of ga4_guide to deploy (lesson 8). Changes nothing in the cloud.

  uv run python scripts/stage_deploy.py

It creates build/ga4_guide/ with:
  *.py                           copied from agents/ga4_guide (agent.py, __init__.py, guardrails.py)
  skills/ga4-context/            the skill, copied INSIDE the agent folder (only this folder is uploaded)
  .env                           ONLY the Google Cloud settings: no Langfuse key, no OTEL lines
  requirements.txt               the packages the cloud image must install (ADK with MCP and BigQuery)
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
for source in SRC.glob("*.py"):  # agent.py, __init__.py, guardrails.py (lesson 9), ...
    shutil.copy2(source, OUT / source.name)
shutil.copytree(ROOT / "skills" / "ga4-context", OUT / "skills" / "ga4-context")

# adk deploy uploads EVERY value in the agent folder's .env as an environment variable,
# so we write a new one with only what the deployed agent needs.
(OUT / ".env").write_text(
    "GOOGLE_GENAI_USE_ENTERPRISE=TRUE\n"
    "GOOGLE_CLOUD_PROJECT=kc-okf-poc-261122\n"
    "GOOGLE_CLOUD_LOCATION=us-central1\n"
)

# Without this file the cloud image gets only google-adk[a2a], which has no `mcp` package, and the
# container fails to start: "cannot import name 'McpToolset'" (lesson 8, first deploy). `gcp` brings BigQuery.
(OUT / "requirements.txt").write_text("google-adk[a2a,agent-identity,mcp,gcp]==2.15.0\n")

(OUT / ".agent_engine_config.json").write_text(json.dumps({
    "identity_type": "AGENT_IDENTITY",  # the agent gets its own identity (a principal), not a shared service account
    "min_instances": 0,                 # scale to zero when idle (default is 1)
    "max_instances": 1,                 # a POC needs one
}, indent=2) + "\n")

for f in sorted(OUT.rglob("*")):
    if f.is_file():
        print(f.relative_to(ROOT), f.stat().st_size, "bytes")
```

**`scripts/runtime.py`** (new `principal` command):

```python
"""Look at, talk to, or delete our deployed agent on Agent Runtime (lesson 8).

  uv run python scripts/runtime.py info   RESOURCE          # name, identity, settings
  uv run python scripts/runtime.py principal RESOURCE        # the IAM member string for this agent (lesson 9)
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


def principal(name: str) -> None:
    """Print the agent's identity in the form IAM commands want: principal://..."""
    agent = client.runtimes.get(name=name)
    print("principal://" + agent.api_resource.spec.effective_identity)


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
    elif command == "principal":
        principal(name)
    elif command == "ask":
        asyncio.run(ask(name, sys.argv[3]))
    elif command == "delete":
        delete(name)
    else:
        sys.exit(__doc__)
```

## Step 12. Commit

```bash
git status --short
git add agents/ga4_guide/guardrails.py agents/ga4_guide/agent.py scripts/stage_deploy.py scripts/runtime.py && git commit -m "Lesson 9: least-privilege roles for the agent identity, guardrails plugin"
```

## Check yourself

1. Why does `roles/bigquery.jobUser` go on the project but `roles/bigquery.dataViewer` on the dataset?
2. Which roles did the agent have before this lesson, and who gave them?
3. A role lets the agent read the whole table. Why can't IAM alone stop it from showing city names?
4. What happens to the model when `before_tool_callback` returns a dict?
5. Why is the "never show cities" rule a plugin and not a callback on `ga4_guide`?
6. Why does `--agent_engine_id` matter when redeploying?

## Send me back

- Which `GRANT` worked in Step 4 (dataset or project)
- The answers from Steps 5 and 6, and any error that remained
- What `adk web` showed for the approval request in Step 10, and whether the city question got blocked
- The `gcloud logging read` lines from Step 11

Next, lesson 10: **Agent Registry**: find our agent there, register the MCP server and the skill.
