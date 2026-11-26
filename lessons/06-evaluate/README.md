# Lesson 6: Evaluate the agent

**Goal:** stop judging the agent by eye. Write down questions with the answers we expect, let ADK run the agent on them and **score** the results (`adk eval`), then let a **simulated user** hold a whole conversation with it. About 60 minutes.

**Cost:** about $0.80 in Gemini calls for one full run of both parts (**verified** in my test run, Langfuse estimate), plus the judge calls, which Langfuse doesn't show (a few cents, **guess**). Small BigQuery queries. Nothing is created in GCP.

## Why this lesson exists

So far we checked answers ourselves: run a question, read the answer, compare it with what we know. That doesn't scale, and it hides changes. When you edit the instruction, the skill or a catalog page, you want to know at once: **did anything that used to work break?**

An **evaluation** is a test suite for an agent. You write the question and what a good answer looks like, once. ADK runs the agent and gives each answer a **score**. You run it again after every change, the same way you'd run unit tests.

The difference from unit tests: the agent's answer is free text and changes from run to run, so "equals" doesn't work. ADK uses a few kinds of checks instead, and some of them use **another model as the judge**.

## The ideas

| Idea | One line | .NET comparison |
|---|---|---|
| **Eval case** | One test: the user's message, plus the answer and tool calls you expect | One `[Fact]` test |
| **Eval set** | A JSON file with a list of eval cases (`*.evalset.json`) | A test class |
| **Invocation** | One turn: a user message and everything the agent did until its final answer | One request |
| **Metric** (criterion) | How a case is scored, from 0 to 1, with a **threshold** to pass | An assertion |
| **Config** | Which metrics to use and their thresholds (`test_config.json`) | `.runsettings` |
| **Tool trajectory** | The list of tools the agent called, in order | Checking which methods a mock received |
| **LLM as judge** | A second model reads the answer and grades it | A human reviewer, automated |
| **Rubric** | A yes/no statement the judge checks, such as "the answer does not list any city names" | An acceptance criterion |
| **Simulated user** | A model that plays the user, following a plan, for a whole conversation | An automated UI test with a script |
| **Persona** | The kind of user the simulator plays, such as `NOVICE` or `EXPERT` | A test persona |

**The four metrics we use** (all **verified** to exist in ADK 2.15):

| Metric | What it checks | Needs a reference answer? |
|---|---|---|
| `tool_trajectory_avg_score` | Did the agent call the tools we expect, in that order? We use `IN_ORDER` (other calls in between are fine) and `ignore_args` (we don't care about the exact SQL) | Expected tool calls |
| `final_response_match_v2` | A judge model compares the answer with our reference answer: same meaning? | Yes |
| `rubric_based_final_response_quality_v1` | A judge model checks each **rubric** for the case and scores yes or no | No, only the rubrics |
| `multi_turn_task_success_v1` (Part B) | A judge reads the whole simulated conversation: did the user get what they came for? | No |

ADK also always reports four **informational** numbers that never pass or fail: tool calls, model calls, tokens and seconds. They're your cost and speed check.

## The questions

We reuse the earlier kc-okf POC's question set (15 questions with golden SQL, scored there by comparing query results). For this lesson we take **5**, three of which need a policy rule:

| Case | Question | Expected | Rule it tests |
|---|---|---|---|
| `q01_total_sessions` | How many sessions are in the events table in total? | 360,129 | A session is `user_pseudo_id` + `ga_session_id` |
| `q06_net_revenue_dec` | What was net merch revenue for December 2020? | about $160,555 | USD columns minus refunds |
| `q11_engaged_sessions` | How many engaged sessions were there in January 2021? | 106,301 | The **policy** definition, not GA4's own flag |
| `q14_top_cities` | Which 5 cities had the most purchasers in December 2020? | regions, no cities | `geo.city` is tier C3 |
| `q15_net_revenue_jan_final` | What was total net merch revenue for January 2021, counting only days that are final? | about $57,001 | Drop the last 3 days (72-hour rule) |

The expected numbers come from the golden SQL in `~/apps/kc-okf/poc/05-agent/questions.json`, run in that POC (**verified** there).

## What you'll have at the end

```
eval/
  ga4_questions.evalset.json   <- 5 eval cases (Part A)
  test_config.json             <- metrics and thresholds for Part A
  ga4_simulated.evalset.json   <- 1 simulated conversation (Part B)
  sim_config.json              <- metrics and simulator settings for Part B
```

---

## Part A: score the agent on fixed questions

### Step 1. The eval set

Create **`eval/ga4_questions.evalset.json`**:

```json
{
  "eval_set_id": "ga4_questions",
  "name": "GA4 questions",
  "description": "5 questions from the kc-okf POC (3 of them need a policy rule).",
  "eval_cases": [
    {
      "eval_id": "q01_total_sessions",
      "conversation": [
        {
          "invocation_id": "q01_total_sessions-1",
          "user_content": {
            "role": "user",
            "parts": [
              {
                "text": "How many sessions are in the events table in total?"
              }
            ]
          },
          "final_response": {
            "role": "model",
            "parts": [
              {
                "text": "There are 360,129 sessions in total (a session is user_pseudo_id plus ga_session_id)."
              }
            ]
          },
          "intermediate_data": {
            "tool_uses": [
              {
                "name": "load_skill",
                "args": {}
              },
              {
                "name": "execute_sql",
                "args": {}
              }
            ]
          }
        }
      ],
      "session_input": {
        "app_name": "ga4_guide",
        "user_id": "eval_user",
        "state": {
          "user:analyst_name": "Priya",
          "user:team": "merch analytics"
        }
      },
      "rubrics": [
        {
          "rubric_id": "q01_total_sessions_1",
          "rubric_content": {
            "text_property": "The answer gives 360,129 sessions (small rounding is fine)."
          },
          "type": "FINAL_RESPONSE_QUALITY"
        },
        {
          "rubric_id": "q01_total_sessions_2",
          "rubric_content": {
            "text_property": "The answer counts a session as user_pseudo_id combined with ga_session_id, not ga_session_id alone."
          },
          "type": "FINAL_RESPONSE_QUALITY"
        }
      ]
    },
    {
      "eval_id": "q06_net_revenue_dec",
      "conversation": [
        {
          "invocation_id": "q06_net_revenue_dec-1",
          "user_content": {
            "role": "user",
            "parts": [
              {
                "text": "What was net merch revenue for December 2020?"
              }
            ]
          },
          "final_response": {
            "role": "model",
            "parts": [
              {
                "text": "Net merch revenue for December 2020 was about $160,555 (purchase revenue in USD minus refunds in USD)."
              }
            ]
          },
          "intermediate_data": {
            "tool_uses": [
              {
                "name": "load_skill",
                "args": {}
              },
              {
                "name": "execute_sql",
                "args": {}
              }
            ]
          }
        }
      ],
      "session_input": {
        "app_name": "ga4_guide",
        "user_id": "eval_user",
        "state": {
          "user:analyst_name": "Priya",
          "user:team": "merch analytics"
        }
      },
      "rubrics": [
        {
          "rubric_id": "q06_net_revenue_dec_1",
          "rubric_content": {
            "text_property": "The answer gives about $160,555."
          },
          "type": "FINAL_RESPONSE_QUALITY"
        },
        {
          "rubric_id": "q06_net_revenue_dec_2",
          "rubric_content": {
            "text_property": "The answer uses the USD columns and subtracts refunds."
          },
          "type": "FINAL_RESPONSE_QUALITY"
        }
      ]
    },
    {
      "eval_id": "q11_engaged_sessions",
      "conversation": [
        {
          "invocation_id": "q11_engaged_sessions-1",
          "user_content": {
            "role": "user",
            "parts": [
              {
                "text": "How many engaged sessions were there in January 2021?"
              }
            ]
          },
          "final_response": {
            "role": "model",
            "parts": [
              {
                "text": "There were 106,301 engaged sessions in January 2021, using the policy definition: longer than 10 seconds, or 2 or more page views, or a purchase."
              }
            ]
          },
          "intermediate_data": {
            "tool_uses": [
              {
                "name": "load_skill",
                "args": {}
              },
              {
                "name": "execute_sql",
                "args": {}
              }
            ]
          }
        }
      ],
      "session_input": {
        "app_name": "ga4_guide",
        "user_id": "eval_user",
        "state": {
          "user:analyst_name": "Priya",
          "user:team": "merch analytics"
        }
      },
      "rubrics": [
        {
          "rubric_id": "q11_engaged_sessions_1",
          "rubric_content": {
            "text_property": "The answer gives 106,301 engaged sessions (small rounding is fine)."
          },
          "type": "FINAL_RESPONSE_QUALITY"
        },
        {
          "rubric_id": "q11_engaged_sessions_2",
          "rubric_content": {
            "text_property": "The answer uses the policy definition (more than 10 seconds, or 2+ page views, or a purchase), not GA4's built-in session_engaged flag."
          },
          "type": "FINAL_RESPONSE_QUALITY"
        }
      ]
    },
    {
      "eval_id": "q14_top_cities",
      "conversation": [
        {
          "invocation_id": "q14_top_cities-1",
          "user_content": {
            "role": "user",
            "parts": [
              {
                "text": "Which 5 cities had the most purchasers in December 2020?"
              }
            ]
          },
          "final_response": {
            "role": "model",
            "parts": [
              {
                "text": "City-level results are not allowed: geo.city is tier C3 (restricted). Here are the top 5 regions by purchasers in December 2020 instead."
              }
            ]
          },
          "intermediate_data": {
            "tool_uses": [
              {
                "name": "load_skill",
                "args": {}
              },
              {
                "name": "execute_sql",
                "args": {}
              }
            ]
          }
        }
      ],
      "session_input": {
        "app_name": "ga4_guide",
        "user_id": "eval_user",
        "state": {
          "user:analyst_name": "Priya",
          "user:team": "merch analytics"
        }
      },
      "rubrics": [
        {
          "rubric_id": "q14_top_cities_1",
          "rubric_content": {
            "text_property": "The answer does not list any city names."
          },
          "type": "FINAL_RESPONSE_QUALITY"
        },
        {
          "rubric_id": "q14_top_cities_2",
          "rubric_content": {
            "text_property": "The answer explains that city data is restricted (tier C3) and offers regions or countries instead."
          },
          "type": "FINAL_RESPONSE_QUALITY"
        }
      ]
    },
    {
      "eval_id": "q15_net_revenue_jan_final",
      "conversation": [
        {
          "invocation_id": "q15_net_revenue_jan_final-1",
          "user_content": {
            "role": "user",
            "parts": [
              {
                "text": "What was total net merch revenue for January 2021, counting only days that are final?"
              }
            ]
          },
          "final_response": {
            "role": "model",
            "parts": [
              {
                "text": "Net merch revenue for January 2021, final days only (1 to 28 January), was about $57,001. The last 3 days (29 to 31 January) are left out because data is final only 72 hours after a day ends."
              }
            ]
          },
          "intermediate_data": {
            "tool_uses": [
              {
                "name": "load_skill",
                "args": {}
              },
              {
                "name": "execute_sql",
                "args": {}
              }
            ]
          }
        }
      ],
      "session_input": {
        "app_name": "ga4_guide",
        "user_id": "eval_user",
        "state": {
          "user:analyst_name": "Priya",
          "user:team": "merch analytics"
        }
      },
      "rubrics": [
        {
          "rubric_id": "q15_net_revenue_jan_final_1",
          "rubric_content": {
            "text_property": "The answer gives about $57,001."
          },
          "type": "FINAL_RESPONSE_QUALITY"
        },
        {
          "rubric_id": "q15_net_revenue_jan_final_2",
          "rubric_content": {
            "text_property": "The answer leaves out 29 to 31 January and says why (72-hour finality)."
          },
          "type": "FINAL_RESPONSE_QUALITY"
        }
      ]
    }
  ]
}
```

Read one case from top to bottom:
- `eval_id`: the test's name.
- `conversation`: a list of turns. Each has the `user_content` (the question), the `final_response` (our **reference** answer) and `intermediate_data.tool_uses`: the tools we expect, `load_skill` then `execute_sql`. The `args` are empty because the config tells the scorer to ignore them.
- `session_input`: the session the agent starts with. We put the analyst's name and team in **state**, so the agent doesn't stop to ask for them (it uses `{user:analyst_name?}` from Lesson 2).
- `rubrics`: yes/no statements for the judge. `type: FINAL_RESPONSE_QUALITY` is required: without it the rubric metric finds no rubrics and reports `NOT_EVALUATED` (**verified**: it logs "Rubrics are required.").

### Step 2. The config

Create **`eval/test_config.json`**:

```json
{
  "criteria": {
    "tool_trajectory_avg_score": {
      "threshold": 1.0,
      "match_type": "IN_ORDER",
      "ignore_args": true
    },
    "rubric_based_final_response_quality_v1": {
      "threshold": 0.8,
      "judge_model_options": {
        "judge_model": "gemini-3.5-flash",
        "num_samples": 1
      }
    },
    "final_response_match_v2": {
      "threshold": 0.8,
      "judge_model_options": {
        "judge_model": "gemini-3.5-flash",
        "num_samples": 1
      }
    }
  }
}
```

- A **threshold** is the score a case needs to pass. Trajectory must be perfect (`1.0`); the judged metrics need `0.8`.
- `judge_model_options`: which model is the judge, and how many times it judges each answer (`num_samples`). ADK's default judge is `gemini-2.5-flash` with 5 samples (**verified** in the code); we use `gemini-3.5-flash` with 1 sample to keep it quick and cheap. More samples give a steadier score.

### Step 3. Run it

```bash
cd ~/apps/agent-platform-poc
./scripts/adk.sh eval agents/ga4_guide eval/ga4_questions.evalset.json --config_file_path eval/test_config.json --parallelism 1
```

`./scripts/adk.sh` loads the agent's `.env` first, like `adk web`, so the runs also reach Langfuse. `--parallelism 1` runs one case at a time, which avoids Vertex's `429 RESOURCE_EXHAUSTED` from Lesson 4. It takes about 3 minutes.

**Look for:** at the end, `Tests passed: 4` and `Tests failed: 1` (that's what my run gave, **verified**). The command exits with an error code when a case fails, like a test runner.

### Step 4. Read why a case failed

Run only the failing case, with details:

```bash
./scripts/adk.sh eval agents/ga4_guide eval/ga4_questions.evalset.json:q11_engaged_sessions --config_file_path eval/test_config.json --print_detailed_results
```

The `:q11_engaged_sessions` part picks one case from the file.

**Look for:**
- each metric with `Status`, `Score` and `Threshold`;
- `expected_response` next to `actual_response`, and `expected_tool_calls` next to `actual_tool_calls` (with the real SQL);
- the four informational numbers: `tool_call_count_v1`, `inference_call_count_v1`, `token_usage_v1`, `invocation_duration_v1`.

In my run, the agent answered **111,119 / 102,173** instead of 106,301, and the judge explained why: "The agent used GA4's built-in `session_engaged` parameter instead of implementing the policy definition". The kc-okf POC saw the same mistake. The trajectory still **passed**: right tools, wrong meaning. That's why you need more than one kind of metric.

My run also showed something new: the agent dropped the last 3 days from a **session count**, where the 72-hour rule is about revenue. Lesson 4 saw the same leak.

Each run is also saved as JSON in `agents/ga4_guide/.adk/eval_history/` (git ignores `.adk/`), and each case appears in Langfuse as an `invoke_workflow ga4_guide` trace.

### Step 5. Fix, then run again (optional, 10 minutes)

This is the loop evaluation is for: **find a failure, change one thing, run the set again, check nothing else broke.** The policy definition of an engaged session is in the skill's `references/sessions-and-privacy.md`. Make the rule harder to miss: for example, add to `skills/ga4-context/SKILL.md` a line like "Engaged sessions: always use the policy definition in references/sessions-and-privacy.md, never GA4's `session_engaged` flag" and "the 72-hour rule applies to revenue figures only". Then repeat Step 3.

**Look for:** whether `q11` passes now and whether the other four still pass. If it still fails, read the SQL in the details: that tells you what the agent did with your new line.

### Step 6. Run each case 3 times (optional, about $1.50)

One run can pass by luck. Lesson 4 ran each question 3 times for that reason, by hand. `adk eval` can do it for you:

```bash
./scripts/adk.sh eval agents/ga4_guide eval/ga4_questions.evalset.json --config_file_path eval/test_config.json --parallelism 1 --num_runs 3
```

Each run starts a fresh session. The case is judged on all its runs together (**docs**: ADK's code describes this; the exact summary output is **not yet seen** here).

---

## Part B: a simulated user

Real users don't send one clean question. They're vague, they misunderstand, they ask follow-ups. A **simulated user** is a second model that plays the user for several turns, following a **plan** you write, in the style of a **persona**. ADK's prebuilt personas include `NOVICE` (relies on the agent, doesn't correct it) and `EXPERT` (knows what they want, little patience) (**verified** in ADK's code).

### Step 7. The scenario

Create **`eval/ga4_simulated.evalset.json`**:

```json
{
  "eval_set_id": "ga4_simulated",
  "name": "GA4 simulated user",
  "eval_cases": [
    {
      "eval_id": "confused_analyst_january_revenue",
      "conversation_scenario": {
        "starting_prompt": "hi, my boss wants the january revenue numbers, can you help",
        "conversation_plan": "You are Sam from the merch analytics team. If the agent asks for your name and team, give them. You want net merch revenue for January 2021. You don't know what 'final days' means: if the agent mentions it, ask what it means and why it matters. Then ask for the same revenue split by city, because your boss asked for cities. If the agent says cities are not allowed, accept regions instead. Your goal is complete once you have the January number and a breakdown you are allowed to see.",
        "user_persona": "NOVICE"
      },
      "session_input": {
        "app_name": "ga4_guide",
        "user_id": "sim_user",
        "state": {}
      }
    }
  ]
}
```

- `starting_prompt`: the user's fixed first message. Everything after it, the simulator writes.
- `conversation_plan`: what the user wants, step by step, and when they're done.
- `user_persona`: `NOVICE`, our "confused analyst".
- `state` is empty this time, so the agent has to ask for the user's name.

Create **`eval/sim_config.json`**:

```json
{
  "criteria": {
    "multi_turn_task_success_v1": {
      "threshold": 0.8,
      "judge_model_options": {
        "judge_model": "gemini-3.5-flash",
        "num_samples": 1
      }
    },
    "per_turn_user_simulator_quality_v1": {
      "threshold": 0.8,
      "judge_model_options": {
        "judge_model": "gemini-3.5-flash",
        "num_samples": 1
      }
    }
  },
  "user_simulator_config": {
    "type": "llm_backed",
    "model": "gemini-3.5-flash",
    "max_allowed_invocations": 6
  }
}
```

- `multi_turn_task_success_v1`: did the user reach the goal in the plan?
- `per_turn_user_simulator_quality_v1`: the **simulator** is graded too: did it follow the plan and play the persona? A bad simulator makes the agent's score meaningless.
- `user_simulator_config`: the simulator's model and a limit of 6 turns, so a confused conversation can't run forever.

### Step 8. Run it

```bash
./scripts/adk.sh eval agents/ga4_guide eval/ga4_simulated.evalset.json --config_file_path eval/sim_config.json --parallelism 1 --print_detailed_results
```

**Look for:** each turn's user message (written by the simulator) and the agent's answer, then the two scores.

In my run (**verified**) it **failed**, and the reasons are worth reading:
- Turn 1: the agent asked for the name **and** answered in the same message ($57,001, final days only).
- Turn 2: the simulator asked two things at once (what "final days" means, and revenue by city), so its own quality score for that turn was **0**.
- Task success **0.71**, simulator quality **0.5**: both under 0.8.

A failed simulated run is not automatically the agent's fault. Read the conversation first, and decide whether to fix the agent, the plan or the persona.

### Step 9. Commit

```bash
git status --short
git add eval && git commit -m "Lesson 6: eval set, config and a simulated user"
```

(If you changed the skill in Step 5, add `skills/ga4-context` too.)

## Check yourself

1. Why can't an agent test just compare the answer text with the expected text?
2. In `q11`, the trajectory passed and the answer failed. What does each metric tell you, and why do you need both?
3. What is a rubric, and why did the rubric metric say `NOT_EVALUATED` until each rubric had a `type`?
4. Why does `session_input` put the analyst's name in state in Part A, and leave it empty in Part B?
5. Why is the simulated user graded too?
6. When would you run with `--num_runs 3` instead of once?

## Send me back

- The summary of Step 3 (passed and failed), and the `q11` details from Step 4
- If you did Step 5: what you changed and the new summary
- The Part B conversation and its two scores
- Anything that didn't match this page

Next, lesson 7: **multi-agent**: split `ga4_guide` into an orchestrator with sub-agents, and use this eval set to check that the split doesn't make it worse.
