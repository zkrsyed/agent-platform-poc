# Lesson 4 results: a skill (`ga4-context`)

Run on 2026-11-26. Everything here is **verified** from Langfuse traces unless marked otherwise. **Status: done.** Baseline = the Lesson 3 agent; skill = the Lesson 4 agent (`SkillToolset` with `skills/ga4-context`).

Method: each question in its own new session, 3 times. The first baseline pair of runs (Q1 A, Q2 A) was done by the user in the browser; the other runs were driven through `adk web`'s HTTP API, so the traces look the same. Vertex returned `429 RESOURCE_EXHAUSTED` for many attempts; failed attempts that never reached a final answer are left out (3 in the skill round).

## Repeatability

| Check | Lesson 3 agent | Lesson 4 agent (skill) |
|---|---|---|
| Q1 (daily revenue): filters on `event_date_dt`, USD columns, refund wrapper | 3 of 3 | 3 of 3 |
| Q1: drops the last 3 days (2021-01-29 to 31) and says so | **0 of 3** (it had the rule in the catalog text and ignored it; showed Jan 31 as $0.00) | **3 of 3** (`DATE_SUB('2021-01-31', INTERVAL 3 DAY)`, said why) |
| Q2 (top cities): city-level results | 1 of 2 attempts ran SQL grouped by `geo.city` (**fail**); 1 passed (weak baseline) | **0 of 3**: all rolled up to region and country and cited tier C3 |
| Q3 ("names of the cities that spent the most"): refused cities? | not run | yes, rolled up to region (1 clean run) |
| `load_skill` called before any SQL | n/a | 7 of 7 clean runs |
| Catalog calls (`search_entries`, `lookup_context`) | every run | **none** in the clean runs |

## Cost (Langfuse estimate)

| | Lesson 3 agent | Lesson 4 agent |
|---|---|---|
| Q1: model calls | 6, 6, 6 | 4, 4, 4 |
| Q1: biggest input (tokens) | 34,586 to 36,307 | 12,419 to 12,608 |
| Q1: cost | $0.117, $0.137, $0.137 (avg $0.130) | $0.073, $0.059, $0.057 (avg $0.063) |
| Q1: seconds | 30.1, 23.1, 32.7 | 20.3, 53.5, 19.6 |
| Q2: calls / biggest input / cost / seconds | 3 / 39,045 / $0.065 / 13.2 (one run, shared a session with Q1: not comparable) | 7, 5, 5 / 14,230, 14,044, 12,862 / $0.106, $0.099, $0.062 / 37.6, 28.1, 25.7 |

Findings:

1. **Q1: about half the cost and a third of the input tokens**, with the right behavior every time. Cost fell from about $0.13 to about $0.06 per question (-52%), biggest input from about 35,000 to about 12,500 tokens. Seconds did not clearly improve (one run took 53.5 s).
2. **Why:** the agent never called the catalog. `load_skill` returned **2,249 characters** (the `SKILL.md` body plus wrapper), and it read one reference file (`net-revenue.md` for Q1, `sessions-and-privacy.md` for Q2). Lesson 3's catalog result was about 75,000 characters in the conversation.
3. **Q2 was not cheaper** (up to $0.106 vs a baseline we can't trust): it made 5 to 7 calls, used `get_table_info` to read the schema (the skill doesn't list every column) and sometimes ran a second query. So the skill saves most when it replaces the catalog lookup, not when the question needs exploration.
4. **The skill's rule was applied unevenly on Q2.** Rule 4 says to drop the last 3 days for daily revenue or any figure called "final". In 2 of 3 Q2 runs the agent also dropped the last 3 days for a plain purchase count (`BETWEEN … '2021-01-28'`), in 1 it did not. The rule's wording is open to reading. Fix: tighten the text ("applies to revenue figures only") and re-measure (**guess** that this fixes it).
5. **Privacy held 3 of 3 on Q2 and 1 of 1 on Q3** with the skill, vs 1 failing SQL in 2 partial baseline attempts. Small numbers; the baseline's failing run is the notable one.
6. **A skill is knowledge, not enforcement.** It made the model follow our rules reliably in these runs, but nothing blocks a bad query. Hard guarantees need the code-level guardrails of Lessons 9 and 11.
7. **The `description` and the instruction did the triggering.** The agent called `load_skill` first in every clean run, as the instruction and ADK's built-in block ask.

## Answers to "Check yourself"

1. **Always in the prompt:** level 1, name + description (314 characters). The `description` matters more than the body because it's all the model sees before deciding to load the skill. A vague description means the skill is never loaded.
2. **Skill vs MCP tool:** a skill is text that enters the prompt (knowledge, nothing runs). An MCP tool runs code on a server and returns a result (an action).
3. **Why filter out `run_skill_script`:** a skill can carry code, and we don't need that. Same idea as Lesson 3's `tool_filter`: the agent never learns a tool it doesn't need exists.
4. **`name` equals the folder name:** the loader checks it (verified in ADK 2.15), so a skill can be found and referenced by one stable name.
5. **Labelling the finality rule as a policy:** the data shows no gap in the last days, so a reader can't verify it from the table. Saying "policy" tells people who to ask if it changes, and keeps us from claiming the data proves it.
6. **Why 3 runs:** one run can't show whether behavior repeats. The baseline missed the 72-hour rule 3 of 3 times (so it was consistently wrong, not random), and the skill got it right 3 of 3. One run of each could have hidden that.
