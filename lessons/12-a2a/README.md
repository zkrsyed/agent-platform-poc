# Lesson 12: A2A, agents calling agents

**Goal:** take lesson 7's `sql_reviewer` out of the analyst's process and run it as **its own agent**, reachable over the **A2A protocol** (Agent2Agent). The analyst then calls it by URL, the way one team's service calls another's. First locally (free except Gemini), then decide whether to deploy it to Agent Runtime.

**Cost:** Part A runs on the laptop; only Gemini costs money. One question ≈ the analyst (4–6 Gemini calls) + the reviewer (about 3 per review) ≈ **$0.15–0.30** (**guess**, from lesson 11's ~$0.11 per question). Ask **two questions at most**. Part C (cloud) is a separate decision.

## Why this lesson exists

In lesson 7, `data_analyst` used `sql_reviewer` through `AgentTool`: the reviewer ran **inside the same Python process**, like calling a function. Real organizations don't work that way: the data-policy team owns the reviewer, deploys it on its own schedule, gives it its own identity, and other teams call it. They might even build it in another framework. A2A is the open protocol for that call: a standard way for one agent to find another, send it a message and get an answer.

## The ideas

| Idea | One line | .NET comparison |
|---|---|---|
| **A2A** (Agent2Agent) | An open protocol (JSON-RPC over HTTP) for one agent to send tasks and messages to another | A REST/gRPC contract between services |
| **Agent card** | A JSON file at `/.well-known/agent-card.json`: the agent's name, description, skills and URL | An OpenAPI document |
| **A2A server** | Wraps an agent so it answers A2A messages. ADK: `to_a2a(agent, port=...)` builds the server **and** the card | Hosting a Web API |
| **`RemoteA2aAgent`** | A stand-in for a remote agent: give it the card URL and use it like a local agent | A typed HTTP client |
| **Local sub-agent vs remote agent** | Local: same process, shared memory, no network. Remote: separate process or company, network, its own identity and deploys | In-process class vs microservice |

**Verified on 2026-11-27 (no Gemini calls):** `to_a2a` serves this card for our reviewer:
```json
{ "name": "sql_reviewer",
  "supportedInterfaces": [{ "url": "http://localhost:8001", "protocolBinding": "JSONRPC", "protocolVersion": "1.0" }],
  "skills": [ "model", "list_skills", "load_skill", "load_skill_resource" ], ... }
```
and `RemoteA2aAgent` reads it.

## The code (already in the repo)

| File | What it is |
|---|---|
| `agents/sql_reviewer/agent.py` | lesson 7's reviewer, unchanged rules, now its own agent (skill only, no BigQuery) |
| `agents/sql_reviewer/a2a_app.py` | `app = to_a2a(root_agent, host="localhost", port=8001)`: the A2A server and card |
| `agents/ga4_a2a/agent.py` | the analyst: skill + BigQuery + `AgentTool(RemoteA2aAgent(name="sql_reviewer", agent_card="http://localhost:8001/.well-known/agent-card.json"))` |

```
lesson 7:  data_analyst ──AgentTool──► sql_reviewer                (same process)
lesson 12: ga4_a2a      ──AgentTool──► RemoteA2aAgent ══A2A══► sql_reviewer server :8001  (another process)
```

---

## Part A: run it locally

### Step 1. Start the reviewer (terminal A, keep it running)

```bash
cd ~/apps/agent-platform-poc
set -a; source agents/ga4_guide/.env; set +a
uv run uvicorn agents.sql_reviewer.a2a_app:app --port 8001
```
**Look for:** `Uvicorn running on http://127.0.0.1:8001`.

### Step 2. Read its agent card (terminal B)

```bash
curl -s http://localhost:8001/.well-known/agent-card.json | jq '{name, description, supportedInterfaces, skills: [.skills[].name]}'
```
**Look for:** the name, the description from `agent.py`, the URL, and the skills. This is everything another agent learns about the reviewer **before** calling it. Free: no Gemini call.

### Step 3. Ask the analyst (terminal B)

```bash
./scripts/adk.sh web agents
```
Open the web UI, choose **ga4_a2a**, **New Session**, ask:
> What was the final net revenue for 2021-01-25? Show the SQL.

**Look for:**
- in the web UI's events: a call to `sql_reviewer` with the question and the SQL, and its reply (APPROVED or a list of problems);
- in **terminal A**: the reviewer's own log lines appear, **in the other process**. That's the A2A call arriving.
- in Langfuse: the analyst's trace shows the `sql_reviewer` call as one step; the reviewer's inside steps are **not** in it (they ran in another process).

### Step 4. Break it on purpose (free)

Stop terminal A (Ctrl+C) and ask again in a **New Session**. **Look for:** what the analyst does when the remote agent is down (an error, a retry, or an answer without review?). Then start terminal A again.

**Send me:** the card from Step 2, a screenshot of Step 3's events, terminal A's lines, and what happened in Step 4.

---

## Part B: compare (no new runs)

| | lesson 7: `AgentTool(sql_reviewer)` | lesson 12: `AgentTool(RemoteA2aAgent(...))` |
|---|---|---|
| Where the reviewer runs | inside the analyst's process | its own process (later: its own deployment) |
| How the analyst finds it | Python import | agent card URL |
| Who can change it | whoever deploys the analyst | the reviewer's owners, without redeploying the analyst |
| Identity in the cloud | the analyst's | its own (Part C) |
| Failure mode | none (same process) | network: down, slow, wrong URL |
| Trace | one trace | one trace per side (unless trace context is passed) (**guess**, Step 3 shows) |

---

## Part C: in the cloud (later, decide first) ☁

Not now. Questions to answer before deploying (**to check**):
1. **Deploy:** can `adk deploy agent_engine` serve the reviewer over A2A on Agent Runtime, and what URL and card does it get? (Lesson 10 showed our deployed ADK agent registers as `CUSTOM`, "Non A2A".)
2. **Auth:** how does a deployed analyst authenticate to a deployed reviewer (agent identity tokens, IAM role on the reviewer)?
3. **Registry:** register the reviewer's agent card in Agent Registry so the analyst finds it by name (lesson 10's pattern).
4. **Gateway:** the lesson plan wanted the call to pass the gateway. The gateway is **off** after lesson 11 (cost); turning it on is lesson 11 Part E.
5. **Cost:** a second deployed agent (idle not billed during the Preview, **docs**) plus Gemini per call.

## Check yourself

1. What does the agent card tell a caller, and where does it live?
2. Why is the reviewer's rule set safer as a separate agent than as a sub-agent?
3. What new failure appears when the reviewer is remote?
4. In lesson 7 the reviewer was an `AgentTool`. What changed in the analyst's code to make it remote, and what didn't?
