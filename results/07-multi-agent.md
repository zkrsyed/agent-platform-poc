# Lesson 7 results: multi-agent

Run on 2026-11-26. Claude built both teams and scored them with Lesson 6's eval set; the user then ran both in `adk web`. Everything here is **verified** (Langfuse traces, saved eval results, screenshots) unless marked otherwise. **Status: done.** The user chose not to repeat Part C (the eval comparison), because Claude's run already covers it.

## What we built

| App | Pattern | Who decides the next step | Members |
|---|---|---|---|
| `agents/ga4_team` | LLM routing (sub-agents + transfer) and agent as a tool (`AgentTool`) | the model | `ga4_team` front desk → `policy_expert` or `data_analyst`; `data_analyst` calls `sql_reviewer` as a tool |
| `agents/ga4_flow` | `Workflow` graph with a review loop | the code | `start_question` (code) → `sql_writer` → `sql_reviewer` → `check_review` (code) → `"fix"` back to the writer (max 3) or `"approved"` to `answer_writer` |

ADK 2.15 deprecates `SequentialAgent`, `ParallelAgent` and `LoopAgent` "in favor of Workflow"; a Workflow "cannot yet be used as an LlmAgent sub-agent" (both from ADK's code).

## The user's runs in `adk web`

Question: "how many engaged sessions were there in January?" (expected by the policy: 106,301).

| | `ga4_team` (3rd message in its session) | `ga4_flow` (New Session) |
|---|---|---|
| Path | `policy_expert` → transfer back to `ga4_team` → transfer to `data_analyst` → skill → `get_table_info` → `sql_reviewer` (tool) → `execute_sql` | `sql_writer` → `sql_reviewer` → `fix` → `sql_writer` → `sql_reviewer` → `approved` → `answer_writer` → `execute_sql` (graph shows **2x** on writer and reviewer) |
| Answer | **106,301** for the month, plus 97,780 "final" (last 3 days dropped, not asked for) | **106,301** |
| Model calls / tokens | 11 / 84,767 | 17 / 59,555 |
| Cost (Langfuse) | $0.177 | $0.169 |

Earlier messages in the `ga4_team` session: a greeting ($0.005, front desk only) and a rule question that went `ga4_team` → `remember_analyst` → transfer to `policy_expert` ($0.02).

Screenshots: [ga4_team](../docs/screenshots/07-ga4-team.webp), [ga4_flow](../docs/screenshots/07-ga4-flow.webp).

## Claude's runs

**Building `ga4_flow`:** the first reviewer **approved** a query that used GA4's `session_engaged` flag (111,119). After adding explicit checks to its instruction ("GA4's own built-in fields do NOT replace our definitions"), the reviewer sent it back, the writer fixed it and the answer was 106,301 (65 s). A reviewer is only as good as its checklist.

**Eval set from Lesson 6, one run each:**

| Case | `ga4_guide` | `ga4_team` | `ga4_flow` |
|---|---|---|---|
| `q01_total_sessions` | pass | pass | pass |
| `q06_net_revenue_dec` | pass | pass | pass |
| `q11_engaged_sessions` | fail (111,119) | **pass** (106,301) | fail (106,166) |
| `q14_top_cities` | pass | pass | fail (regions, but no reason given) |
| `q15_net_revenue_jan_final` | pass | pass | pass |
| **Passed** | 4 of 5 | **5 of 5** | 3 of 5 |
| Tokens per case | 45,444 to 132,910 | 29,771 to 73,850 | **17,947 to 36,530** |
| Cost of the run | about $0.52 | about $0.64 | **about $0.47** |

## Findings

1. **A reviewer fixed Lesson 6's mistake**, in both teams, in the user's runs (106,301 both times). In the eval, `ga4_team` passed 5 of 5.
2. **Results vary from run to run.** `ga4_flow` got 106,301 in the user's run and in Claude's build test, but 106,166 in the eval run. One run of each is not enough to rank them (Lesson 4's lesson again).
3. **In a pipeline, each step knows only what you pass it.** In the eval's `q14`, `answer_writer` returned regions without saying why: it never saw the privacy rule, only the SQL and the verdict.
4. **Small steps use fewer tokens.** `ga4_flow` used the fewest tokens per case and cost the least, although it made the most model calls: each call carries a short instruction and few tools.
5. **Context leaks across a conversation.** In the user's `ga4_team` session, the earlier rule question was about finality, and the engaged-sessions answer added an unasked "final" figure (97,780).
6. **Transfers have a cost.** ADK warned: "Every transfer swaps the system instruction and the tool set, so ... the whole prompt is re-sent uncached after each transfer" (lesson 23).
7. **Guarantee vs request.** In `ga4_team` the instruction *asks* the analyst to call the reviewer; in `ga4_flow` the graph *makes* it run before any SQL. When a step must not be skipped, put it in the graph.

## Q&A from the lesson

- **Sequential, Parallel and Loop agents:** older fixed-order wrappers (in order, at once, repeat). ADK 2.15 replaces all three with one `Workflow` graph: a chain = sequential, a fan-out tuple = parallel, a route pointing back = loop, plus branches and plain Python steps.
- **ReAct vs workflow:** every `Agent` is a ReAct loop (think, call a tool, look, repeat; the model decides). A `Workflow` fixes the order in code; its steps can still be ReAct agents.
- **`AgentTool(agent=sql_reviewer)`:** wraps an agent so another agent can call it like a function with one `request` argument; the caller stays in charge. A sub-agent instead takes over the conversation.
- **`SkillToolset`:** ADK's toolset for reading our one skill (`skills/ga4-context`): `list_skills`, `load_skill`, `load_skill_resource`; `tool_filter` leaves out `run_skill_script`.
