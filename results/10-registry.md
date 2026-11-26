# Lesson 10 results: Agent Registry

Run on 2026-11-26 by the user, with Claude checking schemas and reading the registry (read-only) between steps. Everything here is **verified** (terminal output, the console, Langfuse, adk web) unless marked otherwise. **Status: done.**

## What's in the registry now

| Tab (console) | Count | Ours | The rest |
|---|---|---|---|
| Agents | 47 | `ga4-guide` (us-central1) | 46 × **Workspace Agent** (Google's, one per location) |
| MCP Servers | 15 | **`OKF pages (lesson 5)`** (Runtime "MCP") | 14 Google MCP servers (Runtime "Google MCP") |
| Skills | 1 of ours (+100 Google's) | **`private-ga4-context`**, `STATE_ACTIVE` | Google's skills such as `cloud.google.com-bigquery-migration-validator` |
| Endpoints | 0 | | |

API: `agentregistry.googleapis.com`. Cost: free (registry storage, search and API operations); skill scanning is paid from 2027 and we set it to `DISABLED` (**docs**).

## Step by step

| Step | Result |
|---|---|
| 1. Enable the API | before: "Agent Registry API has not been used in project ... or it is disabled" |
| 2. Our agent | registered automatically in **`us-central1`** (its region), not in `global` |
| 3. Its entry | `protocols.type: CUSTOM` with Agent Runtime's `:query` / `:streamQuery` URLs; attributes `Framework: google-adk` and `RuntimeIdentity: principal://...reasoningEngines/...`. **No agent card** (console: "Non A2A"). Google's Workspace Agent, by contrast, is `A2A_AGENT` with an A2A URL, `protocolVersion 0.3.0` and a `skills` list |
| 4. MCP servers | 14 Google servers named after their APIs: agentregistry, aiplatform, apptopology, backupdr, bigquery, bigquerydatatransfer, bigquerymigration, cloudtrace, compute, dataform, **dataplex**, logging, monitoring, storage |
| 5. Connect via the registry | `get_mcp_toolset("...dataplex...")` connected with the address and auth from the registry and listed **all** the catalog's tools, write tools included (`delete_entry`, `upsert_entry`, `set_entry_group_iam_policy`...). Setting `toolset.tool_filter = [...]` afterwards keeps only the read tools |
| 6. Tool spec | `build/okf_toolspec.json`: 3 tools, 1,485 bytes |
| 7–8. Register `okf-pages` | `gcloud agent-registry services create ... --mcp-server-spec-type tool-spec` worked; it shows as an MCP server with ID `...agentregistry:services:okf-pages`, Runtime "MCP". Its address is `127.0.0.1`, so it can be found but not reached by others until it's on Cloud Run |
| 9. Upload the skill | first try: `400 ... type is required` (`skill.type`). The API's schema (`$discovery/rest?version=v1`) showed the required fields: `type: SIMPLE` and `targetState`. Second try: `private-ga4-context` created (`STATE_CREATING`), revision `rev-...`, `scanState: DISABLED` |
| 10. Activate | `409 The resource is being created and therefore can not be updated yet`. Not needed: `targetState: TARGET_STATE_ACTIVE` at creation made it `STATE_ACTIVE` with a default revision |
| 11. Search | `search "rules for querying GA4 revenue"` found `private-ga4-context` |
| 12. `ga4_registry` agent | see below |

## The agent that finds its skill and tools in the registry

Question: "Why must daily revenue leave out the last 3 days?"

`search_skills` ("1 skill found: private-ga4-context") → `load_skill("private-ga4-context")` → `dataplex_googleapis_com_search_entries` → `dataplex_googleapis_com_lookup_context` → `load_skill_resource("references/net-revenue.md")` from `private-ga4-context` → answer: the 72-hour finality rule, exclude 2021-01-29 to 2021-01-31, citing "Skill Registry: private-ga4-context" and a Knowledge Catalog entry. Langfuse: about 26 s, $0.11.

The agent's code has **no skill folder and no catalog URL**:
- skill: `SkillToolset(registry=GCPSkillRegistry(project_id=..., location="global"))` adds `search_skills`; `load_skill` downloads by name.
- catalog: `registry_mcp_toolset("dataplex.googleapis.com", [...])` finds the server by display name; the registry's toolset class (`AgentRegistrySingleMcpToolset`) prefixes tool names with the server's name.

## Things learned

- `gcloud agent-registry` (our gcloud 588) has agents, mcp-servers, services, bindings, endpoints, but **no skills**: skills go through the REST API.
- When docs and an API disagree, the API's discovery document is the source of truth for field names.
- Scripts that accept a **display name** (`show ga4-guide`) avoid copying long IDs; the lesson's commands use display names.
- The editor's Markdown preview went stale twice; reopen it after the README changes.

## Q&A from the lesson

- **Who made the 46 Workspace Agents?** Google: one A2A agent per location, listed automatically. Only `ga4-guide` is ours.
- **Two scripts:** `registry.py` for agents and MCP servers (list, show, tools); `skill_registry.py` for skills (upload, list, show, activate, search).
- **`search` takes words, not a name:** it matches the question against skill names and descriptions, like the console's search box; agents do the same through `search_skills`.
- **Local skill vs registry skill:** a local skill is carried (copied into every build, updated by redeploying); a registry skill is looked up (one place to update, but the registry must be reachable).
- **Which MCP server does `ga4_registry` use?** Google's Knowledge Catalog server, not our `okf-pages` (which runs only on the laptop).
