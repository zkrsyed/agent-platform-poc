# Agent Platform POC: ADK, Agent Runtime, Identity, Registry, MCP, Skills, A2A

A hands-on learning POC. We build one small agent with Google's **Agent Development Kit (ADK)**, deploy it to **Agent Runtime** on Google Cloud (the platform formerly called Vertex AI, renamed **Gemini Enterprise Agent Platform** in 2026), and then look at everything Google creates around it: **Agent Identity**, **Agent Registry**, logs, traces and CI/CD.

The agent is a **GA4 data guide**. It answers questions about a BigQuery table using the context that was built in the earlier [kc-okf POC](https://github.com/zkrsyed/kc-okf):

- **Knowledge Catalog** through Google's hosted MCP server
- **OKF** pages, packaged as an ADK **skill** and also served by **an MCP server we write ourselves**
- **BigQuery**, so the agent can check its SQL by running it

**Start with [`index.html`](index.html)** (open it in a browser). It has the architecture diagram, the glossary and the lesson list. The same content as plain text is in [`docs/lesson-plan.md`](docs/lesson-plan.md) and [`docs/glossary.md`](docs/glossary.md).

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
index.html            map: diagram, glossary, lessons, status
docs/                 lesson plan and glossary (markdown)
lessons/NN-*/         one README per lesson: explanation, code to paste, commands
agents/ga4_guide/     the ADK agent (agent.py, tools, skills/)
mcp_servers/okf/      our own MCP server that serves OKF pages
eval/                 evalset for `adk eval`
deploy/               deploy script and cloudbuild.yaml (CI/CD)
results/              what happened in each lesson, with evidence
```

## Cost and clean-up

Every cloud resource we create is listed in `results/cloud-resources.md` together with the command that deletes it. Agent Runtime, Cloud Run, Gemini and BigQuery cost money while in use (**guess**: a few US dollars for the whole POC).
