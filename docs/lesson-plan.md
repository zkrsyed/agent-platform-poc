# Lesson plan

**The big idea:** an **agent**, an **MCP server** and a **skill** are three separate things. Each can be built, deployed, versioned and registered on its own. **Agent Identity** says who is calling, **IAM** and **Agent Gateway** decide what that caller may use, and the **Agent Registry** is where everyone finds them.

Status goes `planned` → `in progress` → `done`. Each lesson becomes `lessons/NN-name/README.md` (explanation, code to paste, commands) plus `results/NN-name.md` (what happened, labelled verified / docs / guess). ☁ marks lessons that create cloud resources or cost money, so we ask before running them.

| # | Lesson | You learn | You build / run | Status |
|---|---|---|---|---|
| 0 | **Map** | The whole stack and how the pieces connect | Read `index.html` | done |
| 1 | **Setup** ☁ | uv, gcloud profile, ADC, which APIs exist | `pyproject.toml`; enable APIs | planned |
| 2 | **First ADK agent** | `Agent`, Runner, Session, State, Events | `agents/ga4_guide/agent.py`; `adk web`, `adk run` | planned |
| 3 | **Tools + Google's MCP** | Function tools, toolsets, MCP client, the remote Knowledge Catalog MCP, a BigQuery tool, grounding | Add `McpToolset` for `dataplex.googleapis.com/mcp` and a BigQuery tool | planned |
| 4 | **A skill (local)** | Agent Skills, `SKILL.md`, progressive disclosure, skill vs MCP vs tool | `skills/ga4-context/` made from the kc-okf OKF pages (plus OKF's `okf-consume`); load it with `SkillToolset` | planned |
| 5 | **Your own MCP server** ☁ | The server side of MCP: tools, resources, prompts; stdio vs Streamable HTTP | `mcp_servers/okf/` with FastMCP; run it locally, then on Cloud Run | planned |
| 6 | **Evaluate** | `adk eval`, evalsets, scoring both the tool path and the answer | `eval/` from kc-okf's 15 questions | planned |
| 7 | **Deploy the agent to Agent Runtime** ☁ | Packaging, the staging bucket, Agent Identity on, managed sessions | `deploy/deploy.py`; expect a 403 the first time | planned |
| 8 | **Identity and IAM** ☁ | Principals, the SPIFFE ID, least privilege, callbacks as guardrails | Grant roles to the agent principal; watch the 403 go away | planned |
| 9 | **Registry: agents, MCP servers and skills** ☁ | Registry entries and metadata; Skill Registry (Preview); finding things instead of hard-coding them | Look at the auto-registered agent; register our MCP server; upload the skill to Skill Registry and load it from there; use the MCP server from 3 clients (ADK agent, Claude Code or Gemini CLI, optionally Gemini Enterprise) | planned |
| 10 | **Agent Gateway** ☁ | Egress governance, egress policies per agent principal (`roles/iap.egressor`), CEL rules on `mcp.toolName`, permissive vs ENFORCED, Model Armor | Allow `lookup_entry` but block `modify_entry`; test a prompt-injection string. Check the smallest setup first (VPC / PSC needs) | planned |
| 11 | **A2A** ☁ | Agent cards, `RemoteA2aAgent`, agent vs tool | A small "front-desk" agent finds ga4_guide in the Registry and calls it | planned |
| 12 | **Memory** ☁ | Session vs Memory Bank | Turn on Memory Bank and watch it recall across sessions | planned (optional) |
| 13 | **CI/CD for three deployables** ☁ | A pipeline per deployable (agent, MCP server, skill), eval gate, triggers, WIF; compared with `agents-cli` and Terraform | `deploy/cloudbuild-*.yaml` with triggers on GitHub push | planned |
| 14 | **Tour: what ended up where** | Console and gcloud views of every piece; traces, logs, gateway decisions | A checklist with screenshots | planned |
| 15 | **Score, record, clean up** ☁ | Comparison with kc-okf setups A–C; cost | Run `score.py` as setup D, write up the results, delete the resources | planned |

## The three deployables

| | Agent | MCP server | Skill |
|---|---|---|---|
| What it is | Reasoning loop + instruction + tools | A service that offers tools, resources and prompts over MCP | A folder of know-how (`SKILL.md`, references, scripts) |
| Our example | `agents/ga4_guide` | `mcp_servers/okf` | `skills/ga4-context` |
| Runs on | Agent Runtime | Cloud Run | Nothing: it is content that an agent loads |
| Stored / found in | Agent Registry (auto) | Agent Registry (we register it) | Skill Registry (Preview) / Agent Registry |
| Identity | Its own Agent Identity | Cloud Run service account; callers are checked by IAM and the gateway | n/a (whoever loads it needs read access) |
| .NET comparison | A web app | A Web API | A NuGet content package |

## Request flow (lesson 14 should let you trace this end to end)

1. You, or the front-desk agent via **A2A**, send a question to the agent on **Agent Runtime**.
2. The Runner loads the **session** (and **Memory Bank**), then sends **Gemini** the instruction plus one-line skill summaries.
3. Gemini decides to load the **skill** `ga4-context`, which comes from **Skill Registry**.
4. It calls **Knowledge Catalog MCP** as the **agent identity**. **Agent Gateway** checks the egress policy (is this tool allowed for this principal?) and **Model Armor** checks the content. **IAM** then allows the call.
5. It calls **our OKF MCP server** on Cloud Run, which it found in **Agent Registry**.
6. It runs the SQL with the **BigQuery** tool and answers.
7. Each step is an **event** in the session and a **span** in Cloud Trace. Gateway allow and deny decisions show up in the logs.

## Open checks (Google changes fast)

- The exact deploy command in Nov 2026: `adk deploy agent_engine`, `agents-cli deploy`, or the SDK with `identity_type=AGENT_IDENTITY` (**docs**; to verify in lesson 7).
- Does an auto-registered agent get an agent card, or a `CUSTOM` entry with none? A blog post reports the latter (**guess**; lesson 9).
- How ADK loads a skill from Skill Registry: a `GCPSkillRegistry` with `search_skills` / `load_skill` is reported by a third party (**guess**; lesson 9).
- The smallest Agent Gateway setup for Agent Runtime egress: does it need a VPC, PSC or Cloud NAT, and what does it cost (**guess**; check before lesson 10)?
- Agent Runtime pricing while idle (**to check** before lesson 7).
