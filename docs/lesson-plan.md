# Lesson plan

**The big idea:** an **agent**, an **MCP server** and a **skill** are three separate things. Each can be built, deployed, versioned and registered on its own. **Agent Identity** says who is calling. **Guardrails** in code (ADK plugins) and on the network (**Agent Gateway**) decide what that caller may do. The **Registry** is where everyone finds them. **Evaluation, tracing and optimization** tell you whether the agent works and how to make it better.

The plan follows Google's four pillars: **Build** (lessons 1–7, 18, 22), **Scale** (8, 13), **Govern** (9–12), **Optimize** (6, 16–17, 23), plus **user experience** (14–15).

Each lesson's status goes `planned` → `in progress` → `done`. Each lesson becomes `lessons/NN-name/README.md` (explanation, code to paste, commands) plus `results/NN-name.md` (what happened, labelled verified / docs / guess). ☁ means the lesson creates cloud resources or costs money, so we ask before running it.

| # | Lesson | You learn | You build / run | Status |
|---|---|---|---|---|
| 0 | **Map** | The whole stack and how the pieces connect | Read `index.html` | done |
| 1 | **Setup** ☁ | uv, gcloud profile, ADC, which APIs exist, quotas | `pyproject.toml`; enable APIs | done |
| 2 | **First ADK agent** | `Agent`, Runner, Session, State, Events; the `adk web` dev UI | `agents/ga4_guide/agent.py`; `adk web`, `adk run`, `runner_demo.py`, traces in Langfuse | done |
| 3 | **Tools + Google's MCP** | Function tools, toolsets, MCP client, remote Knowledge Catalog MCP, BigQuery tool, grounding | Add `McpToolset` for `dataplex.googleapis.com/mcp` (3 of its 15 tools) and `BigQueryToolset` (read-only, 1 GB cap) | done |
| 4 | **A skill (local)** | Agent Skills, `SKILL.md`, progressive disclosure, skill vs MCP vs tool | `skills/ga4-context/` built from the kc-okf OKF pages (plus OKF's `okf-consume`), loaded with `SkillToolset` | done |
| 5 | **Your own MCP server** ☁ | MCP server side (tools, resources, prompts); stdio vs Streamable HTTP; securing it on Cloud Run (invoker role, ID tokens) | `mcp_servers/okf/` with `MCPServer` (`mcp` 2.x renamed FastMCP), reading the Studio pages live from Knowledge Catalog (no copied files, no drift), with an optional short cache (freshness vs speed); run it locally over stdio and HTTP with a small `okf_guide` agent; Cloud Run is a separate part we do only after agreeing | done (Part B not run) |
| 6 | **Evaluate (offline + simulated)** | `adk eval`, evalsets, scoring the tool path and the answer; simulated multi-turn users | `eval/` with 5 of kc-okf's 15 questions (3 need a policy rule), trajectory + reference + rubric metrics with a Gemini judge; one simulated `NOVICE` user | done |
| 7 | **Multi-agent in one app** | Orchestrator + sub-agents; LLM routing (`sub_agents`, transfer) vs agent-as-tool (`AgentTool`) vs fixed workflows (`SequentialAgent`, `ParallelAgent`, `LoopAgent`) vs the ADK 2.x graph `Workflow` | `ga4_guide` becomes an orchestrator with `schema_expert`, `sql_writer`, `sql_reviewer`, `answer_writer`; a LoopAgent repeats write → review until the SQL passes; score it against the single agent (quality, latency, tokens) | planned |
| 8 | **Deploy to Agent Runtime** ☁ | Packaging, staging bucket, Agent Identity on, managed sessions | `deploy/deploy.py`; expect a 403 the first time | planned |
| 9 | **Identity, IAM and guardrails in code** ☁ | Principals, SPIFFE ID, least privilege; callbacks vs **ADK plugins**; **tool confirmation** (human in the loop) | Grant roles to the agent principal; a plugin that logs every tool call and blocks or asks before `modify_entry` | planned |
| 10 | **Registry: agents, MCP servers, skills** ☁ | Registry entries and metadata; Skill Registry (Preview); finding things instead of hard-coding them; sharing an agent | Look at the auto-registered agent; register the MCP server; upload the skill and load it from the registry; use the MCP server from 3 clients; optional **Claude Code plugin** | planned |
| 11 | **Agent Gateway and governance policies** ☁ | Egress policy per agent principal, CEL rules on `mcp.toolName`, permissive vs ENFORCED; Model Armor; content security, semantic governance | Allow `lookup_entry`, block `modify_entry` at the network level, and compare with lesson 9's plugin; test a prompt-injection string | planned |
| 12 | **A2A between agents** ☁ | A2A protocol, agent card, `RemoteA2aAgent`, `adk web --a2a`; local sub-agent vs remote agent; agent-to-agent identity (which agent may call which) | Move `sql_reviewer` out as a separately deployed **data policy agent** with its own identity; the orchestrator finds it in the Registry and calls it over A2A, through the Gateway | planned |
| 13 | **Memory** ☁ | Session vs Memory Bank | Turn on Memory Bank and watch it recall across sessions | planned (optional) |
| 14 | **Web GUI** ☁ | A real front end vs the dev UI; calling a deployed agent (query and stream API); user login; the Gemini Enterprise app as a ready-made GUI | A small chat page on Cloud Run with login that talks to the deployed orchestrator | planned |
| 15 | **A2UI (agent-driven UI)** | The A2UI protocol (1.0): declarative UI JSON from a catalog of approved components; renderers; AG-UI and MCP Apps (`render_ui_widget`) compared | The agent returns results as an A2UI table and asks "which revenue definition?" with a picker; render it in `adk web`, then in the lesson 14 page | planned |
| 16 | **Observability: Google vs Langfuse** ☁ | OpenTelemetry; Cloud Trace, Unified Trace Viewer, **Topology**; the same traces in **Langfuse**; LangSmith compared | Send the deployed agents' traces to Cloud Trace and your Langfuse; follow one multi-agent, A2A request in both. Compare, span by span: agent invocations, model calls (tokens, cached tokens, cost), tool calls (arguments and results), MCP spans (`initialize`, `tools/list`, `tools/call`), sub-agent and A2A hops, eval runs. Locally first: `adk web --otel_to_cloud` / `--trace_to_cloud` (**verified** to exist in ADK 2.15) | planned |
| 17 | **Optimize: online eval + prompt optimizer** ☁ | Online evaluation with AutoRaters on live traffic; Google's prompt optimizer vs local `adk optimize` (GEPA); evaluate → change → re-score | Turn on online evaluation; optimize the instructions from lesson 6 failures; redeploy and re-score | planned |
| 18 | **Three ways to build** ☁ | Low-code (**Agent Studio**) vs config (**Managed Agents API**, Preview) vs code (ADK) | Rebuild a cut-down ga4_guide in Studio and with the Managed Agents API; run the same 5 questions on each | planned (optional) |
| 19 | **CI/CD for the deployables** ☁ | A pipeline per deployable (orchestrator, policy agent, MCP server, skill), eval gate, triggers, WIF; update vs re-create; rollback; `agents-cli` and Terraform compared | `deploy/cloudbuild-*.yaml` with triggers on GitHub push | planned |
| 20 | **Tour: what ended up where** | Console and gcloud views of every piece: Runtime, Registry, IAM, Gateway decisions, traces, Topology, threat scanning, Cloud Run, buckets, builds | A checklist with screenshots | planned |
| 21 | **Score, cost, clean up** ☁ | Comparison with kc-okf setups A–C; single agent vs multi-agent; token and cloud cost; quotas | Run `score.py` as setup D (and E for multi-agent), write up results, delete resources | planned |
| 22 | **Same agent in LangGraph** (optional) | LangChain/LangGraph basics: graph, nodes, state, checkpointer; how they map to ADK's Agent, Runner, Session and State; where each framework is stronger; the same Gemini model, project and Langfuse | `agents_langgraph/ga4_guide/`: the lesson 3 agent (Knowledge Catalog MCP + BigQuery) rebuilt in LangGraph and run locally; same 5 questions scored against ADK. Deploy later with the same Agent Runtime lessons (`LanggraphAgent` in the Python SDK, **docs**) | planned (take it after lesson 5; no renumbering needed) |
| 23 | **Caching and cost** | Three places to cache, and what each one trades: (1) **data** in our MCP server (lesson 5's short cache: speed vs freshness); (2) **tool results** in session state (`tool_context.state`) so a second question in the same session doesn't fetch the same page again; (3) **the model's input**: Gemini's automatic (implicit) caching vs ADK's explicit `ContextCacheConfig` on `App` (**verified** in ADK 2.15: starts on a session's 2nd turn, needs a 4,096-token prefix on Gemini 3, does nothing on models without explicit caching). Is gemini-3.5-flash one of them? (**to check**). Implicit caching does happen on gemini-3.5-flash: ga4_guide's later calls had about 7,200 `input_cached_tokens` each (**verified** in Lesson 5) | Measure cached tokens, cost and latency on lesson 6's evalset before and after, and check the eval score doesn't drop | planned (take it after lesson 6, which gives the repeatable runs to measure with) |

## The three deployables

| | Agent | MCP server | Skill |
|---|---|---|---|
| What it is | Reasoning loop + instruction + tools | Service offering tools, resources and prompts over MCP | Folder of know-how (`SKILL.md`, references, scripts) |
| Our example | `agents/ga4_guide` | `mcp_servers/okf` | `skills/ga4-context` |
| Runs on | Agent Runtime | Cloud Run | Nothing: an agent loads it |
| Stored / found in | Agent Registry (auto) | Agent Registry (we register it) | Skill Registry (Preview) / Agent Registry |
| Identity | Its own Agent Identity | Cloud Run service account; callers are checked by IAM and the Gateway | n/a (whoever loads it needs read access) |
| .NET comparison | A web app | A Web API | A NuGet content package |

## Guardrails in two places (lessons 9 and 11)

| | ADK plugin / callback (in code) | Agent Gateway policy (on the network) |
|---|---|---|
| Where it runs | Inside the agent process | Outside the agent, on every outbound call |
| Who can change it | Whoever deploys the agent | The platform or security team |
| Can the agent bypass it? | Yes, if its code changes | No (**docs**) |
| Good for | Logging, asking a human, fixing up arguments | Hard allow/deny per identity and tool, Model Armor |
| .NET comparison | Middleware / action filter | API Management policy + firewall |

## Request flow (lesson 20 should let you trace this end to end)

1. You ask a question in the **web GUI** (lesson 14), which calls the **orchestrator** on **Agent Runtime**.
2. The Runner loads the **session** (and **Memory Bank**). **Plugins** run first, then the orchestrator hands work to its **sub-agents**: `schema_expert` → `sql_writer` ⇄ reviewer.
3. `sql_writer` loads the **skill** `ga4-context` from **Skill Registry**.
4. `schema_expert` calls **Knowledge Catalog MCP** as the **agent identity**. The plugin logs the call. **Agent Gateway** checks the egress policy, **Model Armor** checks the content, and **IAM** allows the call.
5. The SQL goes over **A2A** to the separately deployed **data policy agent** (found in **Agent Registry**). The Gateway checks that this agent may call that one.
6. The approved SQL runs with the **BigQuery** tool. The answer comes back as an **A2UI** table that the GUI renders.
7. Every step is an **event** and a **span** (Cloud Trace and Langfuse). **Online evaluation** scores the answer afterwards.

## Platform parts we leave out (and why)

| Part | Why not here |
|---|---|
| RAG Engine, Vector Search | Our data is a structured BigQuery table; these suit documents. A good later POC |
| Code Execution sandbox | Our agent runs SQL, not Python; we may mention it in lesson 18 |
| Model Garden partner / open models | We stick to Gemini; switching models is one line in ADK |
| CodeMender, AI Content Detection | Not about data agents |
| Colab Enterprise notebooks | Another way to call the same APIs |

## Open checks (Google changes fast)

- The exact deploy command in Nov 2026: `adk deploy agent_engine`, `agents-cli deploy`, or the SDK with `identity_type=AGENT_IDENTITY` (**docs**; to verify in lesson 8).
- Does an auto-registered agent get an agent card, or a `CUSTOM` entry with none? A blog reports the latter (**guess**; lesson 10).
- How ADK loads a skill from Skill Registry: a `GCPSkillRegistry` with `search_skills` / `load_skill` was reported by a third party (**guess**; lesson 10).
- The smallest Agent Gateway setup for Agent Runtime egress (VPC, PSC, Cloud NAT?) and its cost (**guess**; check before lesson 11).
- Whether ADK can send OpenTelemetry traces to Cloud Trace and Langfuse at the same time (**guess**; lesson 16).
- Whether simulated evaluation, online evaluation and the prompt optimizer can be used from ADK or only from the console (**to check**; lessons 6 and 17).
- Whether the agent identity survives a redeploy, the "redeploy trap" from a blog post (**guess**; lesson 19).
- Agent Runtime pricing while idle (**to check** before lesson 8).
- Does the A2UI renderer in the `adk web` bundle render A2UI 1.0, or an older version? Does it need the `a2ui-agent-sdk` package (**guess**; lesson 15)?
- How a deployed Agent Runtime agent is exposed over A2A, and how A2A calls are authenticated with agent identities (**to check**; lesson 12).
- Lesson 11: swap the ADK `BigQueryToolset` for Google's hosted BigQuery MCP server (`https://bigquery.googleapis.com/mcp`, 9 tools, **verified** to list in lesson 3) so Agent Gateway can govern the SQL calls; compare the safety settings (**to check**).
- Lesson 9: the `lookup_context` result carries the same ~36,700-character text twice (`content` and `structuredContent`) and both reach the model (**verified** by sizes in lesson 4). An `after_tool_callback` or plugin could strip one copy; measure the saving.
