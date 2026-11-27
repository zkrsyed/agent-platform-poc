# Lesson 13 results: Memory Bank

Run on 2026-11-27 by the user (Part A, local `adk web` + the deployed agent's Memory Bank), with Claude reading the logs. Everything here is **verified** unless marked otherwise. **Status: done.** Step 4b (a question without "weekly", to show the preference *changing* an answer) and Step 5 (changing the preference) were skipped by choice.

## Setup

- Agent: `agents/ga4_memory` = `ga4_guide` + `preload_memory` + `after_agent_callback` that calls `add_session_to_memory()`.
- Memory: the Memory Bank of the deployed `ga4-guide` (`reasoningEngines/7105399555822190592`, `us-central1`). Nothing new created. Its config had `memory_bank_config` with an **empty** `generation_config` (Google's defaults).
- Sessions stay **local**: `agents/ga4_memory/.adk/session.db` (SQLite). Only memory is in the cloud.

## What happened

| Step | Result |
|---|---|
| 1st start, `--memory_service_uri=agentengine://7105399555822190592` | **404 "The ReasoningEngine does not exist"** on both the search and the save. With a short ID, ADK takes the region from `.env`, which says `global` (for the model, lesson 8). |
| Fix: the **full** name `agentengine://projects/kc-okf-poc-261122/locations/us-central1/reasoningEngines/7105399555822190592` | `Search memory response received.` / `Ingest events request triggered.`, no errors |
| Conversation 1: "I'm Priya from merch analytics. From now on I always want revenue as weekly figures, net of refunds. What was net revenue for 2020-12-07 to 2020-12-13?" | **$59,865.00**, no refunds that week, with the partition filter and net rule. Saved after a short "thanks" in the same session (the save sends the whole session, so the question didn't need asking again). |
| Memory Bank, 5 seconds after the save (12:41:46 → 12:41:51) | **2 facts**: "My name is Priya and I work in merch analytics." and "I want revenue presented as weekly figures, net of refunds." The revenue figure and SQL were **not** kept. |
| Conversation 2, a **new** session: "What was revenue in the week of 2021-01-04?" | **$9,465.00**, net, no refunds. `Search memory response received.` before **each** of the 6 Gemini calls. |
| The Gemini request (adk web → event #2 → Request) | `user_messages[0]` = the memory block ("The following content is from your previous conversations with the user… `<PAST_CONVERSATIONS>` … both facts with timestamps … `</PAST_CONVERSATIONS>`"), `user_messages[1]` = the question |
| After conversation 2's save | still **2** facts: Memory Bank merged the repeats instead of adding copies |
| Clean-up | both memories deleted with the SDK; 0 left |

## Where to see it

- **Console:** Agent Platform → Agents → Deployments → `ga4-guide` → **Memories**. Table: scope (`app_name: ga4_memory`, `user_id: user`), resource name, fact, created, updated. Tiles: retrieved memories count, **generate memories token count** (Memory Bank's own Gemini use), memory LRO latency, mutation count. **Unstructured** vs **Structured** (schemas). It opened **without** asking for the App Hub API (lesson 8 saw a prompt on other pages).
- **Script:** `uv run python scripts/memories.py list`. Prints UTC times and full resource names, which include the project **number**: crop before sharing.
- **Terminal (adk web):** `vertex_ai_memory_bank_service.py` lines for search and ingest.

## Learned

- **Three places for "remembering":** the session (every event, local SQLite here), `user:` state (keys our code writes, carried across that user's sessions) and Memory Bank (facts a model extracts, searched by meaning).
- **`adk web` uses SQLite too** in ADK 2.15 (`.adk/session.db` per agent folder), not RAM. Only our scripts used `InMemorySessionService`.
- **Saving:** ADK sends the whole session with `ingest_events`, fire-and-forget. Memory Bank extracts facts with its own model and consolidates them per scope (app + user). With default settings the facts appeared **within 5 seconds**.
- **Using:** `preload_memory` searches with the user's message before **every** Gemini call and inserts the results as a **transient user message**, not in the system instruction and not saved in the session.
- **The proof is in the request,** not the answer: this answer would have been the same without memory (the question said "week"; the skill already nets refunds). Step 4b would show a preference changing an answer.
- **Overlap:** the name lives in both `user:` state and Memory Bank; the model still called `remember_analyst`.

## Q&A from the session

- **How does the conversation get to Memory Bank?** After each answer, our callback calls `add_session_to_memory()`; ADK sends the session's events (without thinking text) over HTTPS with your Google login, scoped to `{app_name, user_id}`.
- **How are facts extracted, and how often?** Memory Bank's own Gemini model reads the events, keeps facts of certain kinds (preferences, personal details, explicit instructions, key details: **docs**), and merges them with existing ones. ADK sends after every answer; extraction fired within seconds here. The trigger can be configured (`generation_trigger_config`, `force_flush`, **verified** options).
- **How does a later conversation get them?** Same app name and user id. `preload_memory` searches with the new message and adds the matches to the request.
- **What's behind it, SQLite or Redis?** Google doesn't say. It's managed, behind an API, with similarity search (**verified**) over the facts; the storage engine is unknown.
- **Is Memory Bank part of Cloud Run?** It's part of the **Agent Runtime instance** (`memory_bank_config` in its settings), which is a separate service from Cloud Run.
