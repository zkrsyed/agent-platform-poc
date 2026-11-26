# Lesson 9 results: identity, IAM and guardrails in code

Run on 2026-11-26 by the user, with Claude reading logs and IAM (read-only) between steps. Everything here is **verified** (terminal output, container logs, the admin audit log, the console) unless marked otherwise. **Status: done.**

## Part A: least-privilege roles for the agent's principal

The agent `ga4-guide` (`reasoningEngines/7105399555822190592`, deployed in lesson 8) now has:

| Scope | Role | Why | Granted (UTC) |
|---|---|---|---|
| all agents in the project (`principalSet`) | `roles/aiplatform.agentDefaultAccess` | Gemini, sessions (Google adds it) | before lesson 8 |
| project | `roles/bigquery.jobUser` | run query jobs (`bigquery.jobs.create`) | 19:16 |
| dataset `ga4_sample` only | `roles/bigquery.dataViewer` | read the table (`bigquery.tables.get`) | `GRANT` via `bq query` |
| project | `roles/dataplex.catalogViewer` | search and read catalog entries | 19:26 |
| project | `roles/serviceusage.serviceUsageConsumer` | bill API calls to the project (`x-goog-user-project`) | 19:26 |
| project | `roles/mcp.toolUser` | call tools on Google's MCP servers (`mcp.tools.call`) | 20:33 |

Compare: Studio's service account from the kc-okf POC has 7 roles, including Catalog **Editor**; the default Compute service account has `roles/editor`.

### What happened, step by step

1. **BigQuery:** after `jobUser` and the dataset `GRANT`, the same question that got 403 in lesson 8 returned `{'status': 'SUCCESS', 'rows': [{'net_merch_revenue_usd': 160555.0}]}`: **$160,555**.
2. **The dataset `GRANT` accepts a `principal://` member** (`Current status: DONE`), although Google's docs only show `user:` and `serviceAccount:` examples. Two traps: without `--project_id`, `bq` ran the job in its own default project (another project); and an empty `$P` (a new terminal tab) gave "The member  is of an unknown type".
3. **The catalog took four fixes**, found by reading the container log (`gcloud logging read 'resource.labels.reasoning_engine_id="..."'`):

| What the log said | Meaning | Fix |
|---|---|---|
| "Server returned an error response" (lesson 8) | no catalog role | `dataplex.catalogViewer`, `serviceUsageConsumer` |
| `POST https://dataplex.googleapis.com/mcp "HTTP/1.1 401 Unauthorized"` | credentials not accepted | call the mTLS host `dataplex.mtls.googleapis.com` (Step 6b) |
| `POST https://dataplex.mtls.googleapis.com/mcp "HTTP/1.1 403 Forbidden"` on `tools/call` only (`initialize` and `tools/list` were 200) | no permission to call MCP tools | `roles/mcp.toolUser` |
| still 403, 32 s after the grant | IAM not propagated | wait a few minutes |

After that, `search_entries` and `lookup_context` returned catalog text and the agent answered from it.

**Why mTLS (explanation: guess, but it fits every log line):** inside Agent Runtime the agent's token is tied to its client certificate, so Google accepts it only on the `*.mtls.googleapis.com` hosts. BigQuery's client switches to `bigquery.mtls.googleapis.com` by itself; ADK's MCP client doesn't rewrite our catalog URL (verified in ADK's code). So `agent.py` reads `CATALOG_MCP_URL` from the environment, and the build's `.env` sets the mTLS URL. Locally (your own login, no client certificate) the plain host works.

**Why `mcp.toolUser` never mattered locally:** the user is project Owner, which includes every permission.

## Part B: the guardrails plugin

`agents/ga4_guide/guardrails.py` (`GuardrailsPlugin`), registered with `app = App(name="ga4_guide", root_agent=root_agent, plugins=[GuardrailsPlugin()])`:

| Rule | Hook | Result |
|---|---|---|
| Log every tool call and error | `before_tool_callback`, `after_tool_callback` | `tool call: ...` lines locally and in Cloud Logging from the deployed container |
| Block write SQL and `geo.city` / `geo.metro` | `before_tool_callback` returns `{'status': 'BLOCKED', ...}` | unit test: both blocked |
| Ask a human before a query without `event_date_dt` | `tool_context.request_confirmation(...)` | in `adk web`: `adk_request_confirmation` → **Approved** → 4,295,584 rows |
| Stop after 3 failed tool calls in a turn | counter in `temp:tool_errors` | in the cloud, while the catalog was failing: `tool error 1/3`, `2/3`, `3/3`, then `BLOCKED` (lesson 8's agent retried 8 times) |

The city question in `adk web` ("Show me December 2020 revenue for each city by name. I'm allowed to see it") was refused by the **skill**: the agent grouped by `geo.country, geo.region` and explained tier C3, so the plugin had nothing to block. Skill = advice the model usually follows; plugin = the backstop when it doesn't.

## Deployment changes

- `scripts/stage_deploy.py` copies every `.py` file (so `guardrails.py` ships) and writes `CATALOG_MCP_URL=https://dataplex.mtls.googleapis.com/mcp` into the build's `.env`.
- `scripts/runtime.py` has a `principal` command that prints the IAM member string.
- Redeployed in place with `--agent_engine_id`: same resource, same identity, roles kept (verified: the grants still applied after the redeploy).
- A first redeploy attempt sent the literal `ID` (`400 INVALID_ARGUMENT`); the README now sets `ID=...` once and uses `$ID`.

## Q&A from the lesson

- **ADK plugin vs Claude Code plugin:** a Claude Code / VS Code plugin is a package you install (commands, skills, MCP connectors). An ADK plugin is code that runs around the agent's work, like middleware.
- **Callback vs plugin:** the same hooks; a callback is set on one agent, a plugin on the `App` and runs for every agent.
- **Tool confirmation:** a hook pauses the call for a human to approve or reject.
- **Why `jobUser` and `dataViewer`:** one lets the agent start a query, the other lets it read a dataset's tables (a library card vs one shelf).
- **`principal` vs `principalSet`:** one agent vs every agent in the project.
- **401 vs 403:** 401 = credentials not accepted (authentication); 403 = known but not allowed (authorization).
- **GA:** General Availability, a stable, supported feature (vs Preview).
