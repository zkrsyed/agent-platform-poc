# Lesson 23: Caching and cost

**Goal:** make `ga4_guide` cheaper without changing its answers, and **measure** it. We switch on three savings one at a time and count the tokens Gemini was sent.

**Cost:** runs locally; only Gemini costs money. Each measuring run asks 2 questions ≈ **$0.10–0.25** (**guess**, from lesson 11's ~$0.11 per question). The plan is **4 runs, about $0.50–1.00 in total**. Skip run 3 if you want to save; runs 1, 2 and 4 tell most of the story.

## Why this lesson exists

Lesson 11's bill: $41.51 this month, all Gemini. Lesson 11's trace showed why: **one question = 7 Gemini calls and 120,600 input tokens**. The agent loop re-sends **everything so far** on every call: the instruction, the skill text, every tool result. So a big tool result is paid for again on each call that follows it.

The biggest one: the catalog's `lookup_context`. MCP returns its answer **twice**: `content` (text) and `structuredContent` (the same data as JSON), about **36,700 characters each** (lesson 4). Both reach the model.

## The ideas

| Idea | Where it saves | Trade-off | .NET comparison |
|---|---|---|---|
| **Trim tool results** | fewer tokens in every later Gemini call | must not drop anything the model needs | DTO projection |
| **Tool-result cache in session state** | skips repeat calls to the catalog in one conversation (time and API use; **not** Gemini tokens: the saved answer still enters the conversation) | stale if the data changes mid-conversation | per-request memo / `IMemoryCache` per session |
| **Data cache in the MCP server** (lesson 5, `OKF_CACHE_SECONDS`) | fewer calls from the server to the catalog API | freshness | output caching |
| **Implicit caching** (Gemini, automatic) | repeated prompt **prefixes** are billed lower; nothing to set up (lesson 5 saw `input_cached_tokens` ~7,200) | only when the prefix repeats exactly | a query plan cache |
| **Explicit context caching** (ADK `ContextCacheConfig`) | ADK creates a Gemini cache of the conversation's start and reuses it | starts on the **2nd turn**, needs ≥ **4,096** tokens for Gemini 3 models (**ADK docstring**); the cache itself is stored for a fee per hour (**guess**: Vertex pricing) | a prepared statement cache |

**ADK plugin detail (verified in `plugin_manager.py`):** plugins run in list order and ADK **stops at the first plugin that returns something**. So the cache plugin (saves, returns nothing) must come before the trim plugin (returns the trimmed result).

## The code (already in the repo)

| File | What it does |
|---|---|
| `agents/ga4_guide/cost.py` | `TrimMcpPlugin`: drops `structuredContent` when `content` has the text. `ToolCachePlugin`: saves catalog answers (`search_entries`, `lookup_context`, `lookup_entry`) in session state under `cache:TOOL:ARGS`, and answers repeats from there |
| `agents/ga4_guide/agent.py` | three switches, **all off unless set**: `COST_TRIM=1`, `COST_TOOL_CACHE=1`, `COST_CONTEXT_CACHE=1` |
| `scripts/measure_tokens.py` | asks 2 catalog questions in **one** session and prints Gemini calls, input tokens (and how many were cached), output and thinking tokens, and the tools used |

Free test (no Gemini, **verified** 2026-11-27): through ADK's plugin manager, a 73,496-character fake `lookup_context` result reaches the model as **36,761** characters, and the second identical call is answered from the session.

---

## Part A: measure

Run each line once, from the repo folder. Write down the **TOTAL** line of each.

```bash
cd ~/apps/agent-platform-poc
# 1. Baseline: nothing on
uv run python scripts/measure_tokens.py
# 2. Trim the duplicate MCP payload
COST_TRIM=1 uv run python scripts/measure_tokens.py
# 3. + reuse catalog answers in the session
COST_TRIM=1 COST_TOOL_CACHE=1 uv run python scripts/measure_tokens.py
# 4. + Gemini explicit context caching
COST_TRIM=1 COST_TOOL_CACHE=1 COST_CONTEXT_CACHE=1 uv run python scripts/measure_tokens.py
```

**Look for:**
- **Run 1:** the input total for 2 questions (we expect a few hundred thousand tokens), and how much is already `cached` by Gemini's implicit caching.
- **Run 2:** input drops a lot if `lookup_context` was called (**guess**: 30–50%). The answers should be the same.
- **Run 3:** a `[tool_cache] HIT` line if Q2 repeats a Q1 catalog call. Whether it repeats depends on the model's choices; if there's no HIT, the cache had nothing to do (worth knowing too). A HIT saves a catalog call, not tokens, so expect input about the same as run 2.
- **Run 4:** a bigger `cached` share from Q2 on (explicit cache).

Each run's trace also goes to Langfuse (project `agent-platform-poc`), if you want to look at a run span by span.

**Send me:** the four TOTAL lines (and any `[tool_cache] HIT`).

## Part B: decide what to keep

Filled in with the 2026-11-27 runs (details in `results/23-caching.md`):

| Switch | Saving (our run) | Risk | Keep for the deployed agent? |
|---|---|---|---|
| Trim | **−29%** input (215,908 → 153,448 tokens) | low: same text, one copy | **yes**, at the next redeploy |
| Tool cache | 0: no HIT, Q2 made no catalog call | stale only if the catalog changes mid-conversation | no need for now |
| Explicit context cache | not measured: run 4's Q2 stopped at the guardrail (below) | small storage fee; no effect on short sessions | open; implicit caching already covers ~60% |

**Watch out:** lesson 9's guardrail asks a human before a query without `event_date_dt`. In a script nobody answers, so the run stops (`adk_request_confirmation` in the tools list) and its numbers are not comparable.

Turning one on for the deployed agent = add the line to the build's `.env` in `scripts/stage_deploy.py` and redeploy (lesson 8). **Not done in this lesson**; we decide after Part A.

## Check yourself

1. Why does one big tool result cost more than once?
2. Why does the cache plugin have to come before the trim plugin?
3. Implicit vs explicit caching: which one needs setup, and when does each one help?
4. When would a tool-result cache give a wrong answer?
