# Lesson plan

Status: `planned` → `in progress` → `done`. Each lesson becomes `lessons/NN-name/README.md` (explanation, code to paste, commands) and `results/NN-name.md` (what happened, labelled verified / docs / guess). ☁ means the lesson creates cloud resources or costs money, so we ask before it.

| # | Lesson | You learn | You build / run | Status |
|---|---|---|---|---|
| 0 | **Map** | The whole stack and how the pieces connect | Read `index.html` | done |
| 1 | **Setup** | uv, gcloud profile, ADC, which APIs exist | `pyproject.toml`; enable APIs ☁ | planned |
| 2 | **First ADK agent** | `Agent`, Runner, Session, State, Events | `agents/ga4_guide/agent.py`; `adk web`, `adk run` | planned |
| 3 | **Tools + Google's MCP** | Function tools, toolsets, MCP client, remote Knowledge Catalog MCP, BigQuery tool, grounding | Add `McpToolset` for `dataplex.googleapis.com/mcp` and a BigQuery tool | planned |
| 4 | **A skill** | Agent Skills, `SKILL.md`, progressive disclosure, skill vs MCP vs tool | `skills/ga4-context/` from the kc-okf OKF pages (plus OKF's `okf-consume` skill); load with `SkillToolset` | planned |
| 5 | **Your own MCP server** | MCP server side: tools, resources, prompts; stdio vs Streamable HTTP | `mcp_servers/okf/` with FastMCP, run locally, then on Cloud Run ☁ | planned |
| 6 | **Evaluate** | `adk eval`, evalsets, scoring the tool path and the answer | `eval/` from kc-okf's 15 questions | planned |
| 7 | **Deploy to Agent Runtime** | Packaging, staging bucket, Agent Identity on, managed sessions | `deploy/deploy.py` ☁; expect a 403 the first time | planned |
| 8 | **Identity, IAM, Gateway** | Principals, SPIFFE ID, least privilege, Agent Gateway, Model Armor, callbacks as guardrails | Grant roles to the agent principal ☁; optional gateway ☁ | planned |
| 9 | **Registry + A2A** | Registry entries, agent metadata, agent card, MCP server entries; one agent calling another | Inspect the auto-registered agent, register our MCP server, and call it from a small "front desk" agent via A2A | planned |
| 10 | **Memory** | Session vs Memory Bank | Turn on Memory Bank and watch it recall across sessions ☁ | planned (optional) |
| 11 | **CI/CD** | Cloud Build pipeline, eval gate, triggers, WIF; compare with `agents-cli` and Terraform | `deploy/cloudbuild.yaml` and a trigger on GitHub push ☁ | planned |
| 12 | **Tour: what ended up where** | Console and gcloud views of every piece; traces and logs | A checklist with screenshots; optional publish to Gemini Enterprise | planned |
| 13 | **Score, record, clean up** | Compare with kc-okf setups A–C; cost | Run `score.py` as setup D, write results, delete resources ☁ | planned |

## Request flow (what lesson 12 should let you trace end to end)

1. You (or the front-desk agent via **A2A**) send a question to the agent's endpoint on **Agent Runtime**.
2. The Runner loads the **session** (and **Memory Bank**), then asks **Gemini** with the instruction plus the skill summaries.
3. Gemini decides to load the **skill** `ga4-context` (rules such as the city ban and the partition filter).
4. It calls **Knowledge Catalog MCP** to look up the table entry. This call runs **as the agent identity**, passes through **Agent Gateway** (with **Model Armor**) if one is configured, and is allowed by **IAM**.
5. It calls our **OKF MCP server** on Cloud Run for a playbook page.
6. It runs SQL with the **BigQuery tool**, then answers.
7. Every step shows up as a span in **Cloud Trace** and as an event in the session.

## Open checks (Google changes fast)

- Exact deploy command in Nov 2026: `adk deploy agent_engine`, `agents-cli deploy` or the Python SDK `client.agent_engines.create(...)` with `identity_type=AGENT_IDENTITY` (**docs**, to verify in lesson 7).
- Does an auto-registered agent get an agent card, or a `CUSTOM` entry with none? A blog reports the latter (**guess**, to verify in lesson 9).
- Can Agent Gateway and Model Armor be turned on cheaply in a single project (**guess**, lesson 8)?
- Pricing for Agent Runtime while idle (**to check** before lesson 7).
