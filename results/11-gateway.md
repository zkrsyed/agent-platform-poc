# Lesson 11 results: Agent Gateway and policies

Run on 2026-11-26/27 by the user, with Claude reading docs, schemas and logs (read-only) between steps. Everything here is **verified** (terminal output, the console, Cloud Logging) unless marked otherwise. **Status: done.** The gateway is still running at the end of the lesson; Part E of the README turns it off.

## The preflight: a "go"

- `networkservices.googleapis.com` enabled; `agent-gateways list` → `Listed 0 items` (no preview or organization error).
- The console's **Agents → Govern → Gateways** page has **Add gateway**. So Agent Gateway for Agent Runtime works **without an organization** and without an early-preview sign-up, in our project.
- Price: **not found** (gateway docs, overview page; the pricing pages didn't load for us). The gateway's logs call it a `SECURE_WEB_GATEWAY`; that product is billed per hour (**guess**), so we turn it off between lessons.

## What we built (the four pieces)

| # | Piece | Name | Plain words | Seen in |
|---|---|---|---|---|
| 1 | Agent Gateway (Agent-to-Anywhere, Google-managed) | `ga4-egress` | the **door** every outgoing call passes | console: Gateways |
| 2 | Authz extension (IAP, `iapPolicyVersion: V2`) | `ga4-iap-guard` | the **guard** that decides allow/deny | console: Network Services → Service Extensions ("In use by: None": that page counts only load balancers) |
| 2 | Authz policy (`REQUEST_AUTHZ`, `CUSTOM`) | `ga4-egress-authz` | the **hookup**: "this door uses this guard" | `gcloud network-security authz-policies list` only (no console page found) |
| 3 | Access policy (UAP) + policy binding | `ga4-guide-egress` | the **list** the guard reads: which hosts our agent may reach | console: Agents → Govern → Policies (grouped under `ga4-guide`) |
| – | Agent connected to the door | `agent_gateway_config` in the deploy | `ga4-guide` → `ga4-egress` | agent → Service configuration → Deployment details → "Agent to Anywhere (Egress)" |

```
agent ──(deploy setting)──► door ──(hookup)──► guard (IAP) ──(reads)──► list (IAM access policy)
```

## Things the docs had wrong or didn't say (verified)

| Expected (docs or our guess) | What happened |
|---|---|
| Gateway YAML with `governedAccessPath` at the top | gcloud's own schema (`.../schemas/networkservices/v1/AgentGateway.yaml`): `protocols: [MCP]` is **required**, and `governedAccessPath` sits under `googleManaged` |
| The docs' allowlist: one condition with 20 hosts | `EXCEEDS_MAX_CONDITION_LIST_SIZE`: a list may hold **at most 10** items → two rules of 10 (`scripts/egress_rules.py`) |
| `policy-bindings create` after a failed `create` | `POLICY_NOT_FOUND`: just a follow-on error |
| `agent_gateway_config` isn't an `adk deploy` flag | putting it in `.agent_engine_config.json` works: `adk deploy` passes the file's keys to `runtimes.update(config=...)` (read in `cli_deploy.py`) |
| Agent identity principal format | `principal://agents.global.proj-NUMBER...` (no organization) is accepted in access policies |
| The plain catalog host gives 401 (lesson 9) | with `GOOGLE_API_ENABLE_RUNTIME_BOUND_TOKEN=false` (the docs' gateway setting; google-auth's newer name), `POST https://dataplex.googleapis.com/mcp "200 OK"`. Confirms lesson 9's guess: the 401 came from **certificate-bound tokens** |
| IAP's audit log shows "would deny" (`granted=false`) | IAP logged only **4 entries all day** (catalog MCP `initialize`), all `granted: true`, **even for calls the door denied**. Not usable for decisions |

## The dry run (guard in DRY_RUN)

- The **gateway request log** (`networkservices.googleapis.com/gateway_requests`) has one entry per outgoing call: **76** for two questions. Every call went through the door: sessions (`us-central1-aiplatform...:appendEvent`, 26), telemetry (25), Gemini (8), Cloud Resource Manager (2), BigQuery (2), the catalog's MCP (2).
- MCP calls carry the **tool name**: `jsonPayload.agentGatewayInfo.mcpInfo` = `{method: tools/call, parameter: lookup_context}`.
- The decision field is `jsonPayload.authzPolicyInfo.result`. In DRY_RUN it was **ALLOWED for all 65 decided calls**, BigQuery and the catalog too (not on the list). So the dry run shows **what** goes out, not what the rules would block.

## Enforced: a real block

1. List = platform (2 rules) + BigQuery; **catalog left out**.
2. Guard re-imported without `iamEnforcementMode: "DRY_RUN"`.
3. Playground question → the agent still answered (Gemini, BigQuery and its **skill** were reachable; the skill is inside the agent's folder, no network).
4. Gateway log since enforcing:

| Destination | Decision | HTTP |
|---|---|---|
| Gemini, sessions, telemetry, Cloud Resource Manager | ALLOWED | 200 |
| BigQuery | ALLOWED | 200 |
| **`dataplex.googleapis.com` (catalog MCP, `tools/list`)** | **DENIED** | **403** (4×) |

The catalog was blocked **although IAM allows it** (`roles/mcp.toolUser`, lesson 9). The agent worked around it and still **claimed** the rule came "from the data catalog": a wrong source, visible only in the logs and traces.

5. Catalog added back (list = platform + BigQuery + catalog, 4 rules). The guard stays ENFORCED.

## Tool-level rules: not done (docs)

Rules about one MCP tool (`destination.agent_registry.mcp_server.tool.name`) work only for MCP servers registered in the gateway's **own regional** registry. Google's catalog server is in the `global` registry, so the gateway sees it as **unregistered** (`destination.unregistered.host`), and unregistered destinations match only by **host and path**. Blocking `lookup_entry` alone needs the catalog registered in `us-central1` (**to check**: README Step 9).

## Tracing (turned on in this lesson)

- Redeployed with `--otel_to_cloud` (sets `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true`; prompt text **not** captured: `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false`).
- First run logged `PERMISSION_DENIED: Cloud Resource Manager API has not been used...` (ADK looks up the project to label traces) → enabled `cloudresourcemanager.googleapis.com`.
- **Traces tab → Trace view**: one row per question. One question = **20 spans, 26.4 s, 120.6K input / 3.2K output tokens**: 7 Gemini calls, `list_skills`, `load_skill`, `search_entries` and `lookup_context` (MCP), `load_skill_resource`, `execute_sql` (BigQuery job + query). Span view with "only agent invocations" looked empty.
- The Playground's log panel shows only the agent's container logs; the gateway's and IAP's logs are only in **Logs Explorer**. Each log line carries its trace ID.

## Logs Explorer queries that worked

```
# every call through the door
resource.type="networkservices.googleapis.com/Gateway"
resource.labels.gateway_name="ga4-egress"

# only the blocked ones
jsonPayload.authzPolicyInfo.result="DENIED"

# only MCP tool calls
jsonPayload.agentGatewayInfo.mcpInfo.method="tools/call"
```
```bash
gcloud logging read 'resource.type="networkservices.googleapis.com/Gateway" AND resource.labels.gateway_name="ga4-egress" AND jsonPayload.tlsSniHostname="dataplex.googleapis.com"' --project kc-okf-poc-261122 --freshness 1d --limit 100 --format 'table(timestamp, httpRequest.status, jsonPayload.authzPolicyInfo.result, jsonPayload.agentGatewayInfo.mcpInfo.method, jsonPayload.agentGatewayInfo.mcpInfo.parameter)'
```

## Cost check (2026-11-27)

Billing → Reports, this month, by service: **$41.51, all Vertex AI** (Gemini 3.5 Flash); Cloud Storage and Dataplex $0. $22.16 of it on 2026-11-22 (the kc-okf POC). The gateway didn't appear yet (same-day). Budgets: "kc-okf-poc" $20/month (alerts only) and $100/month account-wide. Cost rules are now in `docs/lesson-plan.md`.

## Q&A from the lesson

- **IAM vs IAP:** IAM = Identity and Access Management (the rules). IAP = Identity-Aware Proxy (the guard that checks them on the network). IAP is old: it also guards web apps and SSH; Agent Gateway uses it for outgoing agent calls (V2).
- **Why "proxy":** a middleman that makes the call for you; every call passes it, so it can check, log or block.
- **Hookup vs list:** the authz policy connects the guard to the door; the access policy is the list of what the agent may reach. Both are called "policy".
- **Agent identity vs service account:** IAM roles are just as coarse for both; per-tool control comes from the gateway, whose rules **name** the agent identity (required for Agent Runtime).
- **Cloud Run vs Agent Runtime:** Cloud Run runs any container; Agent Runtime runs agents with sessions, memory, agent identity, gateway support and agent tabs. "Agent Engine" is its old name (`adk deploy agent_engine`, `reasoningEngines/`).
- **Logs vs traces:** logs are lines ("this happened"); a trace is one question's timeline of spans. Each question is its own trace; a session groups them.
- **Why did the agent answer while the catalog was blocked?** A gateway blocks destinations, not knowledge: the same rule was in the skill (no network) and BigQuery was allowed.
