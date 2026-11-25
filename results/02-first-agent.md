# Lesson 2 results: First ADK agent

Run on 2026-11-24 and 2026-11-25. Everything on this page is **verified** unless marked otherwise. **Status: in progress** (Steps 1–5 done; Step 5b Langfuse and Step 6 commit still to do).

## What worked

| Step | Result |
|---|---|
| 1. `adk create … --type code` | Wrote `agent.py`, `__init__.py`, `.env` (`GOOGLE_GENAI_USE_ENTERPRISE=1`, project, `GOOGLE_CLOUD_LOCATION=global`) and a `.gitignore` (`.env`, `.adk/`) |
| 2. `agent.py` | `ga4_guide` with one tool (`remember_analyst`), `{user:analyst_name?}` in the instruction, `output_key="last_answer"` |
| 3. `adk run` | Asked for name and team, called `remember_analyst`, then said it has no data access for the purchases question |
| 4. `adk web` | Same three turns; Events, State, Trace and the agent graph all visible |
| 4b. `sqlite3` on `.adk/session.db` | Every table read, see below |
| 5. `scripts/runner_demo.py` | Ran first time, output below |

## Step 5: the Runner by hand (2026-11-25)

Output of `uv run python scripts/runner_demo.py` (in-memory sessions, user `analyst-1`):

| Turn | What happened |
|---|---|
| 1. "Hi, I'm Priya from the merch analytics team." | `calls tool remember_analyst({'name': 'Priya', 'team': 'merch analytics team'})` → `tool result {'status': 'saved', …}` → `state change: {'user:analyst_name': 'Priya', 'user:team': 'merch analytics team', 'times_remembered': 1}` → model greeting → `state change: {'last_answer': …}` |
| 2. "How many purchases were there in December 2020?" | **No tool call.** The model said it has no query access and offered to write the SQL. Only `last_answer` changed. It did not invent a number |
| After | Session has **6 events** (2 user messages, 1 tool call, 1 tool result, 2 model replies). Its state: `times_remembered`, `last_answer`, `user:analyst_name`, `user:team` |
| A NEW session, same user | Starts with only `{'user:analyst_name': 'Priya', 'user:team': 'merch analytics team'}`: the `user:` keys survive, `times_remembered` and `last_answer` do not |

Findings:

1. **Everything matched the offline test** done before the lesson was written: scoping works as documented.
2. The event stream the script prints is the same stream `adk web` shows in its Events tab and `adk run` prints. Our script was a Runner host with about 50 lines.
3. `InMemorySessionService` left no trace: `session.db` has no `analyst-1` rows (**guess**, not queried; check with `SELECT DISTINCT user_id FROM sessions`).
4. 6 events here vs 8 in the `adk run` session: the earlier sessions had one extra user/model exchange (the model first asked for the team).

## Where the data lives: `agents/ga4_guide/.adk/session.db`

Both `adk run` and `adk web` write to the same SQLite file. It survives restarts: it held both runs, which were separate processes on different days.

| Table | Rows we saw | Meaning |
|---|---|---|
| `user_states` | 2: `(ga4_guide, test_user)` from `adk run` and `(ga4_guide, user)` from `adk web`, each with `analyst_name` and `team` | `user:` keys, stored without the prefix, once per app + user |
| `sessions` | 2, one per conversation; `state` = `last_answer`, `times_remembered` (+ `__session_metadata__.displayName` from `adk web`) | Keys with no prefix are per conversation |
| `app_states` | 0 | No `app:` keys used yet |
| `events` | 8 per conversation | Every step as JSON in `event_data`; `author`, `content`, `actions.state_delta`, `model_version`, `invocation_id` live inside the JSON, not as columns |

Findings:

1. **`adk run` uses user ID `test_user`, `adk web` uses `user`.** So `user:` state set in one is not seen by the other.
2. **State changes are events.** The `user:` keys and `times_remembered` appear in the `state_delta` of the **tool result** event; `last_answer` (from `output_key`) appears on **every** model text event, including the in-between replies.
3. **`adk web` names sessions** by storing `__session_metadata__: {"displayName": "<first message>"}` in session state. Our code never set it.
4. `events` has a foreign key to `sessions` with `ON DELETE CASCADE`.
5. The SQLite shell isn't installed by default on Ubuntu (`sudo apt install sqlite3`; we got 3.45.1). Python's built-in `sqlite3` module works without it.

## Evidence for lesson 3: the agent guesses the schema

With no data or catalog access, the agent refused to invent numbers, as instructed, but it still offered SQL, and each run guessed differently:

| Run | SQL it suggested | Problem |
|---|---|---|
| `adk run` | count `purchase` events where `event_date` is between `20201201` and `20201231` | Plausible, but a guess |
| `adk web` | `… AND _TABLE_SUFFIX BETWEEN '20201201' AND '20201231'` | Wrong: our table is **partitioned** on `event_date_dt`, not sharded into daily tables, so `_TABLE_SUFFIX` doesn't apply |

Grounding the agent in the Knowledge Catalog (lesson 3) and the OKF skill (lesson 4) should remove this guessing (**guess**, to be measured in lesson 6).
