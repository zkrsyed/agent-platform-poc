# Lesson 6 results: evaluate the agent

Run on 2026-11-26 by the user (Claude ran a test pass first). Everything here is **verified** from the saved results in `agents/ga4_guide/.adk/eval_history/` and Langfuse, unless marked otherwise. **Status: done** (optional Steps 5 and 6 not run).

Agent under test: `ga4_guide` as of Lesson 4 (catalog MCP + BigQuery + skill `ga4-context`). Files: `eval/ga4_questions.evalset.json`, `eval/test_config.json`, `eval/ga4_simulated.evalset.json`, `eval/sim_config.json`. Judge and simulator: `gemini-3.5-flash`, 1 judge sample.

## Part A: 5 fixed questions

| Case | Test run (Claude) | User's run | Answer in the user's run |
|---|---|---|---|
| `q01_total_sessions` | pass | pass | 360,129; also added an unasked "final days" count of 350,597 |
| `q06_net_revenue_dec` | pass | pass | $160,555; said no days needed dropping |
| `q11_engaged_sessions` | **fail** | **fail** | 111,119 (all days) and 102,173 (final days), expected 106,301 |
| `q14_top_cities` | pass | pass | refused cities (tier C3), gave the top regions |
| `q15_net_revenue_jan_final` | pass | pass | $57,001, dropped 29 to 31 January and said why |
| **Total** | **4 of 5** | **4 of 5** | |

Per metric on `q11` (both runs): tool trajectory **1.0** (pass), rubric **0.0**, reference match **0.0**. The judge's reason: the agent used GA4's built-in `session_engaged` flag, not the policy definition (more than 10 seconds, or 2+ page views, or a purchase), even though it read `references/sessions-and-privacy.md`, which has that definition. It also applied the 72-hour rule to a session count.

Informational numbers in the user's run: 4 to 9 tool calls per case, 45,444 to 132,910 tokens (`q11` was the most expensive: 9 tool calls, 132,910 tokens), 16 to 53 seconds.

## Part B: simulated user (`NOVICE`)

| | Test run | User's run |
|---|---|---|
| `multi_turn_task_success_v1` | 0.71 (fail) | 0.67 (fail) |
| `per_turn_user_simulator_quality_v1` | 0.5 (fail) | 0.5 (fail) |
| Turns | 2 | 2 |

The conversation (user's run): turn 1, the agent asked for the name and team **and** answered ($57,001, final days only). Turn 2, the simulator gave the name and asked two things at once (what "final" means, and revenue by city); the agent explained finality, refused cities and gave regions.

Why the scores were low:
- The task-success judge counted "no city split" as a miss, although refusing cities is the **correct** behavior and the plan said to accept regions. The judge was too literal.
- It also counted the long turn-2 answer against the agent's own "a few sentences" instruction. That one is fair.
- The simulator broke its plan by asking two things in one turn, so its own quality score was 0 on that turn.

Conclusion: the agent behaved well apart from `q11`; Part B's failure is mostly the test (judge and simulator), not the agent. Read the conversation before blaming the agent.

## Cost

The user's two runs (5 cases + 1 simulated conversation, 7 traces in Langfuse): **$0.67**. The test pass was about $0.77. Judge and simulator calls are not in Langfuse (**guess**: a few cents).

## Things learned while building it

- Rubrics need `"type": "FINAL_RESPONSE_QUALITY"`; without it the rubric metric reports `NOT_EVALUATED` ("Rubrics are required.").
- The efficiency metrics (`tool_call_count_v1`, `inference_call_count_v1`, `token_usage_v1`, `invocation_duration_v1`) are always on and reject a threshold.
- `adk eval` exits with code 1 when any case fails, like a test runner.
- ADK's default judge is `gemini-2.5-flash` with 5 samples; we set `gemini-3.5-flash` with 1.
- Eval runs appear in Langfuse as `invoke_workflow ga4_guide` traces.

## What we learned (Q&A from the lesson)

- **Rubric:** a yes/no checklist line that a judge model checks; the score is the share of lines met.
- **Eval set vs config:** the eval set says what to test (question, reference answer, expected tools, rubrics, starting state); the config says how to grade (metrics, thresholds, judge model). Thresholds live only in the config.
- **Eval set vs simulated eval set:** in an eval set you write every user message; in a simulated one you write only the first message, a plan and a persona, and a model writes the rest. Fixed sets are regression tests; simulated sets test messy, multi-turn behavior.
- **Other tools:** DeepEval and Ragas score answers with the same ideas under other names (G-Eval, faithfulness, context precision/recall); Langfuse and LangSmith store and run evaluations around traces. Google's equivalents: ADK eval, the Vertex AI Gen AI evaluation service, online evaluation and the prompt optimizer (lesson 17). See the table in the lesson README (**docs/guess**).

## Not done

- Step 5 (fix `q11` in the skill and re-run) and Step 6 (`--num_runs 3`). `q11` is a ready-made first case for lesson 17's prompt optimizer.
