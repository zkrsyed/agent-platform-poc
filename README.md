# Agent Platform POC: ADK, Agent Runtime, Identity, Registry, MCP, Skills, A2A

A hands-on learning POC. We build one small agent with Google's **Agent Development Kit (ADK)**, deploy it to **Agent Runtime** on Google Cloud (the platform formerly called Vertex AI, renamed **Gemini Enterprise Agent Platform** in 2026), and then look at everything Google creates around it: **Agent Identity**, **Agent Registry**, logs, traces and CI/CD.

The agent is a **GA4 data guide**. It answers questions about a BigQuery table using the context that was built in the earlier [kc-okf POC](https://github.com/zkrsyed/kc-okf):

- **Knowledge Catalog** through Google's hosted MCP server
- **OKF** pages, packaged as an ADK **skill** and also served by **an MCP server we write ourselves**
- **BigQuery**, so the agent can check its SQL by running it

**The big idea:** an agent, an MCP server and a skill are three separate things you can deploy and register on their own. Agent Identity says who is calling; IAM and **Agent Gateway** decide what that caller may use.

**Start with the map: https://zkrsyed.github.io/agent-platform-poc/** (the same page as [`index.html`](index.html)). It has the architecture diagram, the glossary and the lesson list. The same content as plain text is in [`docs/lesson-plan.md`](docs/lesson-plan.md) and [`docs/glossary.md`](docs/glossary.md).

## How this repo is used

This is a teaching repo. Each lesson in `lessons/NN-name/README.md` explains one idea, gives the code to paste and the commands to run, and says what to look for, in the terminal and in the Cloud console. The learner runs everything. What actually happened goes in `results/NN-name.md`.

Every claim is labelled:

| Label | Meaning |
|---|---|
| **verified** | We ran it and saw it |
| **docs** | From Google's documentation or a spec, not yet checked here |
| **guess** | Our expectation, not checked |

## Layout (it fills in as the lessons go)

```
index.html            map: diagram, lessons, learning journal, troubleshooting, glossary
docs/                 lesson plan, glossary, troubleshooting (markdown), screenshots/
lessons/NN-*/         one README per lesson: explanation, code to paste, commands
agents/ga4_guide/     the main ADK agent (skill, catalog MCP, BigQuery, guardrails plugin) → Agent Runtime (lesson 8)
agents/okf_guide/     a small agent that uses only our MCP server (lesson 5)
agents/ga4_team/      multi-agent: front desk, specialists, reviewer as a tool (lesson 7)
agents/ga4_flow/      multi-agent: Workflow graph with a review loop (lesson 7)
agents/ga4_registry/  finds its skill and catalog tools in Agent Registry (lesson 10)
mcp_servers/okf/      our own MCP server: Studio pages read live from Knowledge Catalog → Agent Registry (lesson 10)
skills/ga4-context/   the skill (SKILL.md + references)                → Agent Registry skills (lesson 10)
eval/                 eval sets and configs for `adk eval` (lesson 6)
scripts/              helpers: adk.sh, stage_deploy.py, runtime.py, registry.py, skill_registry.py, ...
build/                generated deploy copy (git-ignored)
results/              what happened in each lesson, with evidence; cloud-resources.md lists what to delete
```

## Cost and clean-up

Every cloud resource we create is listed in `results/cloud-resources.md` together with the command that deletes it. Agent Runtime, Cloud Run, Gemini and BigQuery cost money while in use (**guess**: a few US dollars for the whole POC).
