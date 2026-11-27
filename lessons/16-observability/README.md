# Lesson 16: observability, Google Cloud Trace vs Langfuse

**Goal:** send **one** agent run to **both** Google Cloud Trace and our Langfuse at the same time, open the same trace in each, and compare what each one shows. Then look at what the deployed agent gives us.

**Cost:**
- 1–2 questions, about **$0.10–0.20** in Gemini (**guess**; with `COST_TRIM=1` from lesson 23 it's cheaper).
- Cloud Trace, Logging and Monitoring charge per amount sent, with free monthly allowances that a few runs won't come near (**guess** from Google's pricing pages, not checked).
- Langfuse is self-hosted: free. Nothing billed per hour.

## Why this lesson exists

Since lesson 2 our local traces go to **Langfuse**, and since lesson 11 the deployed agent's go to **Cloud Trace**. They have never seen the **same** run. So we can't yet say which tool is better for which question, and the lesson plan had an open check: can ADK send to both at once?

## The basics: OpenTelemetry in four words

| Word | Meaning | .NET comparison |
|---|---|---|
| **Span** | one timed step: an agent run, a Gemini call, a tool call | an `Activity` |
| **Trace** | all spans of one request, linked by one **trace id** | a request's `TraceId` |
| **Exporter** | sends finished spans somewhere (Cloud Trace, Langfuse, a file) | an OpenTelemetry exporter in `AddOpenTelemetry()` |
| **Attributes** | key–values on a span: model, token counts, tool name, arguments | `Activity.SetTag` |

ADK makes the spans. **Exporters decide where they go.** Several exporters can run at once, and every one of them gets the **same trace id**.

## How both get the run (verified in the ADK 2.15 code)

- **Langfuse:** the `OTEL_EXPORTER_OTLP_TRACES_*` lines in `agents/ga4_guide/.env`, which `./scripts/adk.sh` loads (lesson 2).
- **Google:** the `--otel_to_cloud` flag adds exporters for **Cloud Trace** (traces), **Cloud Monitoring** (metrics) and **Cloud Logging** (logs).
- ADK adds the OTLP exporter from the environment **next to** Google's (`maybe_set_otel_providers` in `telemetry/setup.py`), so with the flag, both get every span.

```
                         ┌──► Cloud Trace / Logging / Monitoring   (--otel_to_cloud)
adk web ── spans ────────┤
 (one trace id)          └──► Langfuse on homeserver                (OTEL_* in .env)
```

That's verified in the code, **not yet in a real run**. Step 2 checks it.

---

## Part A: one run, two viewers

### Step 1: start adk web with both

```bash
cd ~/apps/agent-platform-poc
COST_TRIM=1 ./scripts/adk.sh web --otel_to_cloud agents
```

Choose **`ga4_guide`**, click New Session, and ask:

> I'm Priya from merch analytics. What was the final net revenue for 2021-01-25?

### Step 2: find the trace id

In `adk web`, open the **Trace** tab and click the top span (`invocation`). Copy its **trace id** (32 hex characters).

- **Langfuse** (`http://localhost:3000`, project `agent-platform-poc`) → **Tracing** → the newest trace. Its id should be the **same** 32 characters.
- **Cloud Trace:** Google Cloud console → **Trace Explorer** (Observability → Trace explorer) → search for the trace id, or filter by the last few minutes.

**If one side is empty:** Langfuse needs `./scripts/adk.sh` (the plain `adk` loads no `.env`). Cloud Trace takes up to a minute to show a trace.

### Step 3: compare, span by span

Fill this in from your screens (I'll help read them):

| Question | Cloud Trace | Langfuse |
|---|---|---|
| Same trace id, same span tree? | | |
| Gemini calls: token counts in and out? **cached** tokens (lesson 23)? | | |
| Cost in dollars per call or trace? | | |
| Tool calls: arguments and results visible? | | |
| The prompt and answer text visible? | | |
| MCP steps (`initialize`, `tools/list`, `tools/call`)? | | |
| Search and filter: by user, session, tool, error? | | |
| Logs next to the trace? | | |

**Guesses to check:**
- Langfuse shows **cost** and **prompts** more readably, because it's built for LLMs.
- Cloud Trace shows **logs next to spans** and keeps everything in the Google project, with its IAM and retention.

### Step 4: logs and metrics (Google only)

`--otel_to_cloud` also sent **logs** and **metrics**.
- **Logs Explorer:** `logName:"adk"`, or open a span in Trace Explorer → **Logs** (**guess**: the exact log name, to check).
- **Metrics Explorer:** search `adk` or `gen_ai` for request counts and durations (**guess**: names to check).

Langfuse keeps traces only: no general logs or metrics.

**Send me:** screenshots of the same trace in both tools, and your filled table.

## Part B: the deployed agent

The deployed `ga4-guide` sends to Cloud Trace since lesson 11. Ask it one question, with lesson 14's page (`uv run uvicorn web.app:app --port 8080`) or:

```bash
uv run python scripts/runtime.py ask reasoningEngines/7105399555822190592 "What was the final net revenue for 2021-01-25?"
```

Then open Agent Platform → Agents → `ga4-guide` → **Traces**, and compare with Step 3:
- **The prompt and answer text are hidden.** `adk deploy --otel_to_cloud` sets `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false` (**verified** in lesson 11): good for privacy, worse for debugging.
- **It can't reach our Langfuse.** Langfuse runs on the home server, reachable only on our private network, so a Google-hosted agent can't send to it. A hosted or public Langfuse could receive them (**guess**; not doing it, because it would need the Langfuse key in the cloud).
- **Topology** (a map of agents and tools) needs an organization, and our project has none (**verified**, lesson 8).

## Part C (optional): a trace across agents

Lesson 12's A2A run: does the reviewer's work show inside the analyst's trace if both processes export? It needs the trace id passed over A2A and the reviewer server set up to export. **To check**, about $0.20. Skip unless curious.

## Part D: when to use which

We fill this in after Part A:

| Use case | Pick | Why |
|---|---|---|
| Debugging prompts and tool calls while building | | |
| Production on Google Cloud (IAM, retention, logs and alerts in one place) | | |
| Comparing cost per question across versions | | |
| LangSmith (LangChain's tool) | not tested | the same idea as Langfuse, hosted, strongest with LangChain/LangGraph (**docs**) |

## Check yourself

1. What does an exporter do, and why can two run at once?
2. Why do both tools show the same trace id?
3. Why is the deployed agent's prompt text hidden in Cloud Trace?
4. Why can't the deployed agent send traces to our Langfuse?
