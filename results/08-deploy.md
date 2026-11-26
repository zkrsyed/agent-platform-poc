# Lesson 8 results: deploy to Agent Runtime

Run on 2026-11-26 by the user. Everything here is **verified** (terminal output, container logs, the console) unless marked otherwise. **Status: done.** The agent stays deployed for lessons 9 to 12.

## What's deployed

| | |
|---|---|
| Resource | `projects/<project number>/locations/us-central1/reasoningEngines/7105399555822190592` |
| Display name | `ga4-guide` |
| Built from | `build/ga4_guide` (made by `scripts/stage_deploy.py`, not committed) |
| Identity type | `AGENT_IDENTITY` |
| Runs as | `agents.global.proj-<project number>.system.id.goog/resources/aiplatform/projects/<project number>/locations/us-central1/reasoningEngines/7105399555822190592` |
| Scaling | `min_instances` 0, `max_instances` 1 |
| Deploy time | 2 min 54 s (second attempt) |

The trust domain is `proj-<number>` because the project has no organization, as the docs say for such projects.

## What it took (four cloud differences)

1. **`.env` is uploaded.** `adk deploy` turns every line of the agent folder's `.env` into an environment variable; ours holds the Langfuse key. `stage_deploy.py` writes a clean `.env` with three `GOOGLE_*` lines.
2. **Only the agent folder is uploaded.** The skill is copied into `build/ga4_guide/skills/`, and `agent.py` looks for it next to itself first.
3. **The model's location.** `gemini-3.5-flash` returned `404 NOT_FOUND` in `us-central1` and works on `global`; `--region` overrides `GOOGLE_CLOUD_LOCATION`. `agent.py` now pins it: `Gemini(model="gemini-3.5-flash", client_kwargs={"enterprise": True, "location": "global"})`.
4. **Packages.** The **first deploy failed**: "The Reasoning Engine's container failed to start". The container log (`gcloud logging read 'resource.labels.reasoning_engine_id="..."'`) showed `ImportError: cannot import name 'McpToolset' from 'google.adk.tools.mcp_tool'`. Without a `requirements.txt` the image installs only `google-adk[a2a]`, which has no `mcp`. ADK deleted the failed instance itself. Fix: `requirements.txt` with `google-adk[a2a,agent-identity,mcp,gcp]==2.15.0` (checked first in a clean Python 3.11 environment). The second deploy succeeded.

## The first question: the deliberate 403

`runtime.py ask ... "What was net merch revenue for December 2020?"`

| Call | Result |
|---|---|
| Gemini | worked (agent identities get default platform access) |
| `load_skill_resource` | worked (a file inside the agent) |
| `execute_sql` | **403**: "User does not have `bigquery.jobs.create` permission in project" |
| `get_table_info` | **403**: "Permission `bigquery.tables.get` denied on table" |
| `search_entries`, `lookup_context` (catalog MCP) | "MCP tool execution failed: Server returned an error response" (the 403 is hidden behind a generic message) |

The agent retried about 8 failing calls (once with a made-up project `ga4-sample`, which the BigQuery tool's project restriction blocked), then explained the permission error, showed the SQL it would run, and asked for the analyst's name (a deployed session starts with empty state). "User" in BigQuery's message means the agent's principal, not the person asking.

## The console (Agents → Scale → Deployments → `ga4-guide`)

| Tab or page | What we saw | Why |
|---|---|---|
| Playground | works, like `adk web` | |
| Sessions | a session ID; details need App Hub | `apphub.googleapis.com` not enabled |
| Traces, Dashboard | "not available" / "No data" | deployed without `--otel_to_cloud`, which is what sets `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY` (from ADK's deploy code); maybe also a delay (**guess**) |
| Identity, Topology, Security | greyed out | App Hub; Topology also says "A project owned by an organization is required" |
| Memory Bank | lists the agent; details need App Hub | |
| Agent Registry | "Enable Agent Registry API" | lesson 10 |
| Policies, Gateways | API or network setup | lesson 11; may also need an organization (**to check**) |
| "Outdated dependencies" banner | asks for ADK ≥ 1.18 | we run 2.15; the banner can't read our versions (**guess**) |

Nothing was enabled; each of these is planned in a later lesson, with a console check.

## Q&A from the lesson

- **Agent identity vs a shared service account:** with a shared account, every agent gets the same permissions and the logs can't tell them apart; with agent identity each deployed agent is its own principal, gets only its own roles, appears by name in audit logs, and disappears when deleted.
- **Principal:** "who is making this call", the thing IAM checks (like .NET's `ClaimsPrincipal`). `principal://` marks the string as a principal ID; `reasoningEngines/ID` is the one deployed agent.
- **Who is "who"?** Two calls, two principals: you → the agent (you), the agent → BigQuery (the agent). The agent does not borrow your permissions.
- **Locally:** `google.auth.default()` picks up your Application Default Credentials, so every call is you. Deployed, the same line picks up the agent's identity. Where it runs decides who it is.
- **`stage_deploy.py`:** assembles a clean upload folder (like `dotnet publish` output): code, skill inside, safe `.env`, `requirements.txt`, deploy config.
- **`runtime.py`:** a remote control: `info` (details and identity), `ask` (send a question, print tool calls and results), `delete`.
