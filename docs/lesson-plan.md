# Lesson plan

**The big idea:** an **agent**, an **MCP server** and a **skill** are three separate things. Each can be built, deployed, versioned and registered on its own. **Agent Identity** says who is calling. **Guardrails** in code (ADK plugins) and on the network (**Agent Gateway**) decide what that caller may do. The **Registry** is where everyone finds them. **Evaluation, tracing and optimization** tell you whether the agent works and how to make it better.

The plan follows Google's four pillars: **Build** (lessons 1–6, 15), **Scale** (7, 12), **Govern** (8–11), **Optimize** (6, 13–14).

Each lesson's status goes `planned` → `in progress` → `done`. Each lesson becomes `lessons/NN-name/README.md` (explanation, code to paste, commands) plus `results/NN-name.md` (what happened, labelled verified / docs / guess). ☁ means the lesson creates cloud resources or costs money, so we ask before running it.

| # | Lesson | You learn | You build / run | Status |
|---|---|---|---|---|
| 0 | **Map** | The whole stack and how the pieces connect | Read `index.html` | done |
| 1 | **Setup** ☁ | uv, gcloud profile, ADC, which APIs exist, quotas | `pyproject.toml`; enable APIs | done |
| 2 | **First ADK agent** | `Agent`, Runner, Session, State, Events | `agents/ga4_guide/agent.py`; `adk web`, `adk run` | in progress |
| 3 | **Tools + Google's MCP** | Function tools, toolsets, MCP client, remote Knowledge Catalog MCP, BigQuery tool, grounding | Add `McpToolset` for `dataplex.googleapis.com/mcp` and a BigQuery tool | planned |
| 4 | **A skill (local)** | Agent Skills, `SKILL.md`, progressive disclosure, skill vs MCP vs tool | `skills/ga4-context/` built from the kc-okf OKF pages (plus OKF's `okf-consume`), loaded with `SkillToolset` | planned |
| 5 | **Your own MCP server** ☁ | MCP server side (tools, resources, prompts); stdio vs Streamable HTTP; securing it on Cloud Run (invoker role, ID tokens) | `mcp_servers/okf/` with FastMCP; run it locally, then on Cloud Run | planned |
| 6 | **Evaluate (offline + simulated)** | `adk eval`, evalsets, scoring the tool path and the answer; simulated multi-turn users with personas | `eval/` built from kc-okf's 15 questions; one simulated "confused analyst" persona | planned |
| 7 | **Deploy the agent to Agent Runtime** ☁ | Packaging, staging bucket, Agent Identity on, managed sessions | `deploy/deploy.py`; expect a 403 the first time | planned |
| 8 | **Identity, IAM and guardrails in code** ☁ | Principals, SPIFFE ID, least privilege; callbacks vs **ADK plugins**; **tool confirmation** (human in the loop) | Grant roles to the agent principal; write a plugin that logs every tool call and blocks or asks before `modify_entry` | planned |
| 9 | **Registry: agents, MCP servers, skills** ☁ | Registry entries and metadata; Skill Registry (Preview); finding things instead of hard-coding them; sharing an agent | Look at the auto-registered agent; register the MCP server; upload the skill and load it from the registry; use the MCP server from 3 clients; package skill + MCP as a **Claude Code plugin** (optional) | planned |
| 10 | **Agent Gateway and governance policies** ☁ | Egress policy per agent principal, CEL rules on `mcp.toolName`, permissive vs ENFORCED; Model Armor; content security and semantic governance | Allow `lookup_entry`, block `modify_entry` at the network level, and compare with lesson 8's plugin; test a prompt-injection string. Check the smallest setup first | planned |
| 11 | **A2A** ☁ | Agent card, `RemoteA2aAgent`, agent vs tool | A small "front-desk" agent finds ga4_guide in the Registry and calls it | planned |
| 12 | **Memory** ☁ | Session vs Memory Bank | Turn on Memory Bank and watch it recall across sessions | planned (optional) |
| 13 | **Observability: Google vs Langfuse** ☁ | OpenTelemetry; Cloud Trace, the Unified Trace Viewer, **Topology**; the same traces in **Langfuse**; LangSmith compared | Send the deployed agent's traces to Cloud Trace and your Langfuse; compare one request in both | planned |
| 14 | **Optimize: online eval + prompt optimizer** ☁ | Online evaluation with AutoRaters (LLM-as-judge) on live traffic; the prompt optimizer; evaluate → change → re-score loop | Turn on online evaluation; run the optimizer on lesson 6 failures; redeploy and re-score | planned |
| 15 | **Three ways to build** ☁ | Low-code (**Agent Studio**) vs config (**Managed Agents API**, Preview) vs code (ADK); when to use which | Rebuild a cut-down ga4_guide in Studio and with the Managed Agents API; run the same 5 questions on each | planned (optional) |
| 16 | **CI/CD for three deployables** ☁ | A pipeline per deployable, eval gate, triggers, WIF; update vs re-create (and whether the agent identity survives a redeploy); rollback; `agents-cli` and Terraform compared | `deploy/cloudbuild-*.yaml` with triggers on GitHub push | planned |
| 17 | **Tour: what ended up where** | Console and gcloud views of every piece: Runtime, Registry, IAM, Gateway decisions, traces, Topology, threat scanning, buckets, builds | A checklist with screenshots | planned |
| 18 | **Score, cost, clean up** ☁ | Comparison with kc-okf setups A–C; token and cloud cost; quotas and 429s | Run `score.py` as setup D, write up results, delete resources | planned |

## The three deployables

| | Agent | MCP server | Skill |
|---|---|---|---|
| What it is | Reasoning loop + instruction + tools | Service offering tools, resources and prompts over MCP | Folder of know-how (`SKILL.md`, references, scripts) |
| Our example | `agents/ga4_guide` | `mcp_servers/okf` | `skills/ga4-context` |
| Runs on | Agent Runtime | Cloud Run | Nothing: an agent loads it |
| Stored / found in | Agent Registry (auto) | Agent Registry (we register it) | Skill Registry (Preview) / Agent Registry |
| Identity | Its own Agent Identity | Cloud Run service account; callers are checked by IAM and the Gateway | n/a (whoever loads it needs read access) |
| .NET comparison | A web app | A Web API | A NuGet content package |

## Guardrails in two places (lessons 8 and 10)

| | ADK plugin / callback (in code) | Agent Gateway policy (on the network) |
|---|---|---|
| Where it runs | Inside the agent process | Outside the agent, on every outbound call |
| Who can change it | Whoever deploys the agent | The platform or security team |
| Can the agent bypass it? | Yes, if its code changes | No (**docs**) |
| Good for | Logging, asking a human, fixing up arguments | Hard allow/deny per identity and tool, Model Armor |
| .NET comparison | Middleware / action filter | API Management policy + firewall |

## Request flow (lesson 17 should let you trace this end to end)

1. You, or the front-desk agent via **A2A**, send a question to the agent on **Agent Runtime**.
2. The Runner loads the **session** (and **Memory Bank**). **Plugins** run first, then the request goes to **Gemini** with the instruction plus one-line skill summaries.
3. Gemini loads the **skill** `ga4-context` from **Skill Registry**.
4. It calls **Knowledge Catalog MCP** as the **agent identity**. The plugin logs the call. **Agent Gateway** checks the egress policy, **Model Armor** checks the content, and **IAM** allows the call.
5. It calls **our OKF MCP server**, which it found in **Agent Registry**.
6. It runs SQL with the **BigQuery** tool and answers.
7. Every step is an **event** in the session and a **span** in Cloud Trace (and in Langfuse). **Online evaluation** scores the answer afterwards.

## Platform parts we leave out (and why)

| Part | Why not here |
|---|---|
| RAG Engine, Vector Search | Our data is a structured BigQuery table; these suit documents. A good later POC |
| Code Execution sandbox | Our agent runs SQL, not Python; we may mention it in lesson 15 |
| Model Garden partner / open models | We stick to Gemini; switching models is one line in ADK |
| CodeMender, AI Content Detection | Not about data agents |
| Colab Enterprise notebooks | Another way to call the same APIs |

## Open checks (Google changes fast)

- The exact deploy command in Nov 2026: `adk deploy agent_engine`, `agents-cli deploy`, or the SDK with `identity_type=AGENT_IDENTITY` (**docs**; to verify in lesson 7).
- Does an auto-registered agent get an agent card, or a `CUSTOM` entry with none? A blog reports the latter (**guess**; lesson 9).
- How ADK loads a skill from Skill Registry: a `GCPSkillRegistry` with `search_skills` / `load_skill` was reported by a third party (**guess**; lesson 9).
- The smallest Agent Gateway setup for Agent Runtime egress (VPC, PSC, Cloud NAT?) and its cost (**guess**; check before lesson 10).
- Whether ADK can send OpenTelemetry traces to Cloud Trace and Langfuse at the same time (**guess**; lesson 13).
- Whether simulated evaluation, online evaluation and the prompt optimizer can be used from ADK or only from the console (**to check**; lessons 6 and 14).
- Whether the agent identity survives a redeploy, the "redeploy trap" from a blog post (**guess**; lesson 16).
- Agent Runtime pricing while idle (**to check** before lesson 7).
