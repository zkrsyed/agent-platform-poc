# Lesson 23 results: caching and cost

Run on 2026-11-27 by the user (Part A, local), with Claude reading the output. Everything here is **verified** unless marked otherwise. **Status: done**, with one open point: explicit context caching was not measured (run 4's Q2 stopped at the guardrail; not re-run, by choice).

## The runs

`scripts/measure_tokens.py`: 2 catalog questions in one session, numbers from Gemini's own `usage_metadata`.

| Run | Switches on | Gemini calls | Q1 input | Q2 input | **Total input** | Cached by Gemini | vs baseline |
|---|---|---|---|---|---|---|---|
| 1 | none (baseline) | 9 (7 + 2) | 142,123 | 73,785 | **215,908** | 132,952 (62%) | — |
| 2 | trim | 8 (6 + 2) | 102,335 | 51,113 | **153,448** | 99,704 (65%) | **−62,460 (−29%)** |
| 3 | trim + tool cache | 8 (6 + 2) | 100,503 | 51,824 | **152,327** | 91,614 (60%) | −63,581 (−29%) |
| 4 | trim + tool cache + context cache | 7 (6 + **1**) | 101,520 | 25,176 ⚠️ | 126,696 ⚠️ | 69,327 (55%) | not comparable |

Output was 775–1,906 tokens and thinking 3,267–4,129 per run: small next to input.

Tools, every run: Q1 `remember_analyst, load_skill, search_entries, lookup_context, load_skill_resource, execute_sql`; Q2 `execute_sql` only. The model never called the catalog again in Q2: it answered from what was already in the conversation.

⚠️ **Run 4, Q2:** tools were `execute_sql, adk_request_confirmation`. The model wrote a query without the `event_date_dt` filter, and lesson 9's `GuardrailsPlugin` (rule 3) paused to ask a human to approve a full-table scan. The script can't answer, so Q2 ended after 1 Gemini call. Its numbers are small because it **stopped**, not because of caching.

## What each switch did

| Switch | What it is | Effect here |
|---|---|---|
| `COST_TRIM` (`TrimMcpPlugin`) | **not a cache**: removes the duplicate `structuredContent` copy from catalog answers | **−29%** total input (Q1 −28%, Q2 −31%). Q2 got cheaper too although it didn't call the catalog: the trimmed answer from Q1 stays in the conversation and is re-sent on every later call |
| `COST_TOOL_CACHE` (`ToolCachePlugin`) | saves catalog answers in session state; a repeat call with the same arguments is a **HIT** and skips the catalog | **no HIT, no effect**: Q2 made no catalog call. A HIT would save a catalog call, **not** Gemini tokens (the saved answer still enters the conversation) |
| `COST_CONTEXT_CACHE` (ADK `ContextCacheConfig`) | ADK asks Gemini to store the conversation's start and reuse it, from turn 2 | **not measured**: turn 2 stopped at the guardrail. Q1 matched run 3, as expected (it starts on turn 2) |
| Gemini implicit caching | automatic, nothing to set up | **55–65%** of input reported as cached in every run |

## Learned

- **Trim is the win:** half-size tool results are paid for less on every later call. Same tools, same answers.
- **Three caches, two of them at Google.** Tool cache = ours, in the session. Implicit cache = Google notices a repeated start of a request by itself. Explicit context cache = ADK tells Google to store it (guaranteed, small storage fee per hour, **guess** from Vertex pricing).
- **Gemini reports one `cached` number** (`cached_content_token_count`) for both implicit and explicit caching, so the column can't tell them apart.
- **Q1's cached share varies by itself** (46K in run 3, 58K in run 4 with the same Q1 setup): implicit caching isn't guaranteed.
- **The tool cache fits agents that repeat catalog calls**; ours keeps the answer in the conversation instead.
- **Guardrails pause unattended runs.** A plugin can ask for human confirmation (`tool_context.request_confirmation`), not only a tool (`require_confirmation=True`). A test script hits that pause and stops.

## Part B decision

| Switch | Saving | Risk | Keep for the deployed agent? |
|---|---|---|---|
| Trim | −29% input | low: same text, one copy | **yes**, at the next redeploy (not done in this lesson) |
| Tool cache | 0 here | stale only if the catalog changes mid-conversation | no need for now |
| Explicit context cache | unknown | storage fee; nothing on short sessions | open; implicit caching already covers ~60% |

Cost of the lesson: 4 runs, roughly $0.40–0.80 (**guess**, from ~$0.11 per question; not checked in billing).

## Q&A from the session

- **What does HIT mean?** Not an acronym: you looked in the cache and found it. The opposite is a miss.
- **Where is the tool cache saved?** In session state, under `cache:TOOL:ARGS`: process memory for `measure_tokens.py` and local `adk web`, Google's session store for the deployed agent. Session state isn't sent to Gemini unless the instruction pulls it in with `{...}`.
- **Why plugins?** One place that wraps every tool call of the App, without touching the MCP tools ADK builds for us; easy to switch on and off. Like ASP.NET middleware.
- **Why isn't the context cache a plugin?** It's about the request to Gemini, not tool calls, and ADK has it built in: one setting on `App`.
- **Is human-in-the-loop a plugin?** It can be: our guardrail plugin asks for confirmation. It can also be set on a tool (`FunctionTool(fn, require_confirmation=True)`). Either way ADK pauses, emits `adk_request_confirmation`, and resumes after the answer. (Correction: Claude first said it wasn't a plugin thing.)
