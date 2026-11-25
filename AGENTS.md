# For AI agents working in this repo

This is a **teaching** POC. The human is learning Google's agent stack (ADK, Agent Runtime, Agent Identity, Agent Registry, Agent Gateway, MCP, skills, A2A, CI/CD) one lesson at a time. They come from .NET and SQL Server.

## Rules

- **Teach; don't do the work for them.** For each lesson, write `lessons/NN-name/README.md`: what the idea is (one line, with a .NET analogy), the code to paste (with its target path), one command per code block, and what to look for afterwards. The human pastes and runs. Run read-only checks only when they ask.
- **Ask before** creating cloud resources, spending money, enabling APIs, pushing to GitHub or deleting anything. Never delete files: move them to `trash/`.
- **Label claims** as **verified** (run and seen), **docs** (from documentation) or **guess**. Google renames products often; check current docs before stating a command or a name.
- **Record** each lesson's outcome in `results/NN-name.md`, and every cloud resource in `results/cloud-resources.md` along with its delete command.
- **Keep `index.html` current.** It is hand-written: when a lesson changes status, update its badge in the lesson list there and in `docs/lesson-plan.md`.
- Never commit secrets, `.env`, personal emails, billing IDs or other project IDs.

## Environment

- GCP project: `kc-okf-poc-261122` (shared with the kc-okf POC, which holds the GA4 table and the Knowledge Catalog context set). gcloud profile: `kc-okf`.
- Data: `kc-okf-poc-261122.ga4_sample.events`. Context: the published context set and OKF export from kc-okf step 4.
- Related repo: https://github.com/zkrsyed/kc-okf (its `AGENTS.md` lists the verified facts).

## Learning journal

`index.html` has a "Learning journal" section. After each lesson, and during a lesson when something worth keeping comes up, add or extend that lesson's `<details class="lesson">` block: what we did, key ideas, verified findings, and the learner's questions with plain-language answers (`<div class="qa">`). Use SVG diagrams when a picture helps. Keep the newest lesson open.
