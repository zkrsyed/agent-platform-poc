# Lesson 7: Multi-agent

**Goal:** split our one agent into a **team** of small agents, in the two ways ADK offers: a front desk that **hands the conversation over** to specialists (the model decides), and a **fixed pipeline** of steps with a review loop (the code decides). Then use Lesson 6's eval set to check whether the team is actually better than one agent. About 75 minutes.

**Cost:** a few test questions in `adk web` (cents), plus one eval run per team (about $0.50 to $0.65 each, **verified** in my test runs, Langfuse estimate). Small BigQuery queries. Nothing is created in GCP.

## Why this lesson exists

`ga4_guide` does everything in one agent: greets, reads the rules, writes SQL, runs it, explains. Its instruction keeps growing, and Lesson 6 showed one mistake it keeps making: for engaged sessions it uses GA4's own flag instead of our policy's definition.

A **team** splits the job, like a real data team: a front desk, a policy expert, an analyst, a reviewer who checks the SQL before it runs. Each member has a short instruction and only the tools it needs. The reviewer is the interesting part: a second look catches mistakes the writer makes.

But a team isn't free: more model calls, more time, more tokens. So we don't assume it's better. We **measure** it with the Lesson 6 eval set.

## The ideas

| Idea | One line | .NET comparison |
|---|---|---|
| **Sub-agent + transfer** | An agent lists other agents as `sub_agents`; the model calls `transfer_to_agent`, and the other agent takes over the conversation | A front controller forwarding the request to another controller |
| **LLM routing** | The model reads each agent's `description` and decides who handles the message | A router whose rules are written in plain words |
| **Agent as a tool** (`AgentTool`) | One agent calls another like a function: sends a request, gets one answer back, keeps control | Calling a service method |
| **Workflow** | A graph of steps (**nodes**) joined by **edges**; the code decides what runs next | A state machine, or a workflow engine |
| **Node** | One step: an agent, or a plain Python function | An activity |
| **Route** | A label a node emits (`"approved"`, `"fix"`) that picks the next edge | A `switch` on a result |
| **`output_key` + `{placeholder}`** | An agent saves its answer in session state (`draft_sql`); the next agent's instruction reads it with `{draft_sql}` | Passing a DTO between steps |

**About `SequentialAgent`, `ParallelAgent` and `LoopAgent`:** older ADK tutorials use these to run agents in order, side by side, or in a loop. In ADK 2.15 all three are **deprecated "in favor of Workflow"** (**verified**: the warning is in ADK's code). So we use `Workflow`. One limit from the same warning: a Workflow "cannot yet be used as an LlmAgent sub-agent", so our pipeline is its own app, not a member of the front desk team.

**The two teams we build:**

```
ga4_team (the model decides)                 ga4_flow (the code decides)

  ga4_team  (front desk)                       START
   |-- transfer --> policy_expert                |
   |                (explains rules, no SQL)   start_question   (code: reset)
   '-- transfer --> data_analyst                 |
                    (writes + runs SQL)        sql_writer  <--------+
                      '-- tool --> sql_reviewer   |                  |
                                                sql_reviewer         | fix
                                                  |                  |
                                                check_review  (code) +
                                                  | approved
                                                answer_writer  (runs SQL, answers)
```

---

## Part A: a team where the model decides (`ga4_team`)

### Step 1. The agent

Create **`agents/ga4_team/__init__.py`** (the same tracing guard as `ga4_guide`, with its own name in the first line):

```python
"""ga4_team package. Importing it switches on tracing when the OTEL_* settings are present."""

from google.adk.telemetry.setup import maybe_set_otel_providers
from opentelemetry import trace

# `adk web` installs its own exporters at startup; `adk run` and plain scripts don't.
# So only act if nobody has installed a tracer provider yet.
if isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider):
    maybe_set_otel_providers()

from . import agent as agent  # noqa: E402
```

Create **`agents/ga4_team/agent.py`**:

```python
"""ga4_team (lesson 7): a front desk agent that hands the conversation to specialists.

    ga4_team (front desk) --transfer--> policy_expert   (explains rules, no SQL)
                          --transfer--> data_analyst    (writes and runs SQL)
                                            |
                                            +-- calls sql_reviewer as a TOOL before running SQL

Here the MODEL decides who handles each message (LLM routing), and one agent uses
another agent like a function (agent as a tool).
"""

from pathlib import Path

import google.auth
from google.adk.agents import Agent
from google.adk.integrations.bigquery import BigQueryCredentialsConfig, BigQueryToolset
from google.adk.integrations.bigquery.config import BigQueryToolConfig, WriteMode
from google.adk.skills import load_skill_from_dir
from google.adk.tools import AgentTool, ToolContext
from google.adk.tools.skill_toolset import SkillToolset

PROJECT = "kc-okf-poc-261122"
MODEL = "gemini-3.5-flash"
SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "ga4-context"

_creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])


def _skill() -> SkillToolset:
    return SkillToolset(
        skills=[load_skill_from_dir(SKILL_DIR)],
        tool_filter=["list_skills", "load_skill", "load_skill_resource"],
    )


bigquery = BigQueryToolset(
    tool_filter=["get_table_info", "execute_sql"],
    credentials_config=BigQueryCredentialsConfig(credentials=_creds),
    bigquery_tool_config=BigQueryToolConfig(
        write_mode=WriteMode.BLOCKED,
        maximum_bytes_billed=1_000_000_000,
        max_query_result_rows=50,
        compute_project_id=PROJECT,
    ),
)


def remember_analyst(name: str, team: str, tool_context: ToolContext) -> dict:
    """Remember who the analyst is, so later answers can address them by name.

    Args:
        name: The analyst's first name.
        team: The team the analyst works in.
    """
    tool_context.state["user:analyst_name"] = name
    tool_context.state["user:team"] = team
    return {"status": "saved", "name": name, "team": team}


# Used as a TOOL by data_analyst: it gets a request, answers once, and control goes back.
sql_reviewer = Agent(
    name="sql_reviewer",
    model=MODEL,
    description="Reviews a BigQuery SQL query for the GA4 table against the data team's rules. "
    "Send it the analyst's question and the SQL. It replies APPROVED or lists the problems.",
    instruction="""You review a SQL query against the rules in the skill `ga4-context` (load it,
and the reference file the question needs). You do not run queries. The request contains the
analyst's question and the SQL.

Be strict. Check, one by one:
- every numbered rule in the skill that applies to this question;
- every metric the question names (sessions, engaged sessions, net revenue, buyers...): if the
  reference files define it, the SQL must compute exactly that definition. GA4's own built-in
  fields (for example the `session_engaged` parameter) do NOT replace our definitions;
- the 72-hour rule applies only to revenue figures or figures the analyst calls "final".

If it passes every check, reply with exactly: APPROVED
Otherwise reply with a short list of the problems and how to fix each one.""",
    tools=[_skill()],
)

# Sub-agents: the front desk TRANSFERS the conversation to them.
policy_expert = Agent(
    name="policy_expert",
    model=MODEL,
    description="Explains the data team's rules and definitions for the GA4 table "
    "(what a term means, why a rule exists). Does not run queries.",
    instruction="""You explain the data team's rules and definitions for the GA4 table, in plain
words and a few sentences, using the skill `ga4-context` (load it, and a reference file if needed).
You never write or run SQL. If the analyst asks for a number, transfer back to `ga4_team`.""",
    tools=[_skill()],
)

data_analyst = Agent(
    name="data_analyst",
    model=MODEL,
    description="Answers questions that need numbers from the GA4 table, by writing and running SQL.",
    instruction="""You answer data questions about `kc-okf-poc-261122.ga4_sample.events`.
1. Load the skill `ga4-context` and the reference file the question needs. Use `get_table_info`
   only if you need a column.
2. Write ONE read-only SQL query. Before running it, call `sql_reviewer` with the question and
   the SQL. If it does not reply APPROVED, fix the SQL and ask again (at most 3 times).
3. Run the approved SQL with `execute_sql` and answer in a few sentences: the number, the SQL,
   and any rule that changed the answer. Never invent figures.
If the analyst asks what a rule means, transfer back to `ga4_team`.""",
    tools=[_skill(), bigquery, AgentTool(agent=sql_reviewer)],
)

root_agent = Agent(
    name="ga4_team",
    model=MODEL,
    description="Front desk for GA4 questions: greets the analyst and routes to a specialist.",
    instruction="""You are the front desk of the GA4 data team.
The analyst: {user:analyst_name?} (team: {user:team?}).
If the name is empty, ask for their name and team once, then call `remember_analyst`.

You don't answer data questions yourself. Route each message:
- What a rule, term or definition means, or why a rule exists -> transfer to `policy_expert`.
- Anything that needs numbers from the table -> transfer to `data_analyst`.
If a message asks both, start with the number.""",
    tools=[remember_analyst],
    sub_agents=[policy_expert, data_analyst],
)
```

Read it from the bottom up:
- `root_agent` is the **front desk**. It has one tool (`remember_analyst`) and two **sub-agents**. Its instruction says who gets which kind of message. ADK gives it a `transfer_to_agent` tool automatically, because it has sub-agents.
- `policy_expert` and `data_analyst` are the specialists. Their **`description`** matters: it's what the front desk reads when it decides where to send a message.
- `data_analyst` has `AgentTool(agent=sql_reviewer)` in its tools. To the analyst, the reviewer looks like a function with one `request` argument. The analyst stays in charge and decides when to ask again.
- The difference: a **transfer** hands the whole conversation over; an **agent tool** asks one question and gets one answer back.

### Step 2. Try it in the dev UI

```bash
cd ~/apps/agent-platform-poc && ./scripts/adk.sh web agents
```

Pick **ga4_team** in the dropdown, open a **New Session**, and send two messages:

1. `What does it mean that a day is final?`
2. `How many engaged sessions were there in January 2021?`

**Look for** in the Events tab:
- the event's author changing: `ga4_team`, then `policy_expert` for message 1;
- `transfer_to_agent` calls. For message 2 in my run, `policy_expert` first transferred **back** to `ga4_team`, which transferred to `data_analyst`;
- `sql_reviewer` calls with the question and the SQL in `request`. In my run the analyst called it 3 times;
- the graph view (top left) showing the team as a tree.

**What happened in my run (verified):** message 1 went to `policy_expert`, which explained the 72-hour rule. Message 2 went to `data_analyst`, which got 106,166 engaged sessions for the month, close to the policy's 106,301 but not exact (its session key was slightly different). It also gave a "final days" figure nobody asked for: the previous message was about finality, and that leaked into this answer.

The server log also printed a warning worth knowing: `App "ga4_team" can transfer between agents but has no context_cache_config. Every transfer swaps the system instruction and the tool set ... the whole prompt is re-sent uncached after each transfer.` That's a cost of transfers, and lesson 23 comes back to it.

---

## Part B: a pipeline where the code decides (`ga4_flow`)

### Step 3. The workflow

Create **`agents/ga4_flow/__init__.py`**:

```python
"""ga4_flow package. Importing it switches on tracing when the OTEL_* settings are present."""

from google.adk.telemetry.setup import maybe_set_otel_providers
from opentelemetry import trace

# `adk web` installs its own exporters at startup; `adk run` and plain scripts don't.
# So only act if nobody has installed a tracer provider yet.
if isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider):
    maybe_set_otel_providers()

from . import agent as agent  # noqa: E402
```

Create **`agents/ga4_flow/agent.py`**:

```python
"""ga4_flow (lesson 7): the same job as ga4_guide, split into steps in a fixed graph (a Workflow).

    question -> start_question -> sql_writer -> sql_reviewer -> check_review --approved--> answer_writer
                    ^                               |
                    +------------- fix -------------+   (at most 3 tries)

Each step is a small agent with only the tools it needs. The code, not the model,
decides what runs next.
"""

from pathlib import Path

import google.auth
from google.adk.agents import Agent, Context
from google.adk.events import Event
from google.adk.integrations.bigquery import BigQueryCredentialsConfig, BigQueryToolset
from google.adk.integrations.bigquery.config import BigQueryToolConfig, WriteMode
from google.adk.skills import load_skill_from_dir
from google.adk.tools.skill_toolset import SkillToolset
from google.adk.workflow import Workflow

PROJECT = "kc-okf-poc-261122"
MODEL = "gemini-3.5-flash"
SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "ga4-context"
MAX_TRIES = 3

_creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])


def _bigquery(tools: list[str]) -> BigQueryToolset:
    return BigQueryToolset(
        tool_filter=tools,
        credentials_config=BigQueryCredentialsConfig(credentials=_creds),
        bigquery_tool_config=BigQueryToolConfig(
            write_mode=WriteMode.BLOCKED,
            maximum_bytes_billed=1_000_000_000,
            max_query_result_rows=50,
            compute_project_id=PROJECT,
        ),
    )


def _skill() -> SkillToolset:
    return SkillToolset(
        skills=[load_skill_from_dir(SKILL_DIR)],
        tool_filter=["list_skills", "load_skill", "load_skill_resource"],
    )


sql_writer = Agent(
    name="sql_writer",
    model=MODEL,
    description="Writes one BigQuery SQL query for the analyst's question.",
    instruction="""You write ONE read-only BigQuery SQL query for the analyst's question about
`kc-okf-poc-261122.ga4_sample.events`. Load the skill `ga4-context` first and follow its rules;
read a reference file only when the question needs it. Use `get_table_info` only if you need a column.

Reviewer feedback on your last draft (empty on the first try): {review?}

Reply with the SQL only, no explanation, no code fences.""",
    tools=[_skill(), _bigquery(["get_table_info"])],
    output_key="draft_sql",
)

sql_reviewer = Agent(
    name="sql_reviewer",
    model=MODEL,
    description="Checks a draft SQL query against the data team's rules.",
    instruction="""You review a SQL query against the rules in the skill `ga4-context` (load it,
and the reference file the question needs). You do not run the query.

Draft SQL:
{draft_sql}

Be strict. Check, one by one:
- every numbered rule in the skill that applies to this question;
- every metric the question names (sessions, engaged sessions, net revenue, buyers...): if the
  reference files define it, the SQL must compute exactly that definition. GA4's own built-in
  fields (for example the `session_engaged` parameter) do NOT replace our definitions;
- the 72-hour rule applies only to revenue figures or figures the analyst calls "final".

If it passes every check, reply with exactly: APPROVED
Otherwise reply with a short list of the problems and how to fix each one.""",
    tools=[_skill()],
    output_key="review",
)


def start_question(ctx: Context):
    """Plain code: clear what the last question left behind (tries and old feedback)."""
    ctx.state["tries"] = 0
    ctx.state["review"] = ""


def check_review(ctx: Context, review: str):
    """Plain code, no model: decide where the graph goes next."""
    tries = ctx.state.get("tries", 0) + 1
    ctx.state["tries"] = tries
    if review.strip().upper().startswith("APPROVED") or tries >= MAX_TRIES:
        return Event(route="approved")
    return Event(route="fix")


answer_writer = Agent(
    name="answer_writer",
    model=MODEL,
    description="Runs the approved SQL and answers the analyst.",
    instruction="""Run this SQL with `execute_sql` (project kc-okf-poc-261122), exactly as written:
{draft_sql}

Reviewer's verdict: {review}

Then answer the analyst's question in a few sentences: give the number, show the SQL, and
mention any rule that changed the answer (for example, that the last 3 days were left out).
If the reviewer did not approve, say that the query may break a rule. Never invent figures.""",
    tools=[_bigquery(["execute_sql"])],
)

root_agent = Workflow(
    name="ga4_flow",
    description="Answers GA4 data questions with a write -> review -> run pipeline.",
    edges=[
        ("START", start_question, sql_writer, sql_reviewer, check_review),
        (check_review, {"approved": answer_writer, "fix": sql_writer}),
    ],
)
```

Read it in this order:
- `root_agent = Workflow(...)` is the whole app. `edges` is the graph. `("START", start_question, sql_writer, sql_reviewer, check_review)` is a **chain**: each step runs after the previous one. `(check_review, {"approved": answer_writer, "fix": sql_writer})` is a **routing map**: where to go for each route.
- `start_question` and `check_review` are plain Python functions. A function becomes a node, and its parameters are read from session state by name (`review: str` reads `state["review"]`). `check_review` returns `Event(route=...)`: that's how a node picks the next edge.
- The **loop**: the `"fix"` route goes back to `sql_writer`, which reads the reviewer's feedback through `{review?}` (the `?` means "empty if not set"). `MAX_TRIES` stops it after 3 rounds.
- Each agent saves its reply with `output_key` (`draft_sql`, `review`), and the next one reads it with `{draft_sql}`. That's how steps pass work to each other.
- Each agent has only the tools it needs: the writer can look up the table but **can't run SQL**; the reviewer has only the skill; only `answer_writer` can run queries.
- `start_question` resets `tries` and `review`, so the second question in a session doesn't inherit the first one's feedback. (I hit exactly that while building it.)

### Step 4. Try it

In `adk web`, pick **ga4_flow**, open a **New Session**, and ask:

`How many engaged sessions were there in January 2021?`

**Look for** in the Events tab: `sql_writer`, then `sql_reviewer`, then a `route` of `fix` or `approved`, and on `fix` a second round of `sql_writer` and `sql_reviewer`.

**What happened in my run (verified):** the writer used GA4's own `session_engaged` flag (Lesson 6's mistake). The reviewer **rejected** it: "GA4's built-in `session_engaged` parameter must not replace our explicit definition". The route was `fix`, the writer rewrote the query with the policy definition, the reviewer said `APPROVED`, and `answer_writer` returned **106,301**, the correct number. 65 seconds.

One honest detail: my first reviewer **approved** the wrong query. It only caught the mistake after I added explicit checks to its instruction ("GA4's own built-in fields do NOT replace our definitions"). A reviewer is only as good as its checklist.

---

## Part C: is the team better? Measure it

### Step 5. Run Lesson 6's eval set on both teams

```bash
./scripts/adk.sh eval agents/ga4_team eval/ga4_questions.evalset.json --config_file_path eval/test_config.json --parallelism 1
./scripts/adk.sh eval agents/ga4_flow eval/ga4_questions.evalset.json --config_file_path eval/test_config.json --parallelism 1
```

Same questions, same metrics, same thresholds as Lesson 6. Only the agent changes. That's what makes the comparison fair.

**My results (verified, one run each):**

| Case | `ga4_guide` (Lesson 6, your run) | `ga4_team` | `ga4_flow` |
|---|---|---|---|
| `q01_total_sessions` | pass | pass | pass |
| `q06_net_revenue_dec` | pass | pass | pass |
| `q11_engaged_sessions` | **fail** (111,119: GA4's flag) | **pass** (106,301) | **fail** (106,166: close, but a slightly different calculation) |
| `q14_top_cities` | pass | pass | **fail** (gave regions, but didn't say why cities are restricted) |
| `q15_net_revenue_jan_final` | pass | pass | pass |
| **Passed** | **4 of 5** | **5 of 5** | **3 of 5** |
| Tokens per case | 45,444 to 132,910 | 29,771 to 73,850 | **17,947 to 36,530** |
| Model calls per case | 4 to 9 | 7 to 11 | 8 to 14 |
| Seconds per case | 16 to 53 | 27 to 77 | 19 to 101 |
| Cost of the run (Langfuse) | about $0.52 | about $0.64 | **about $0.47** |

What the numbers say:

1. **The team with a reviewer fixed Lesson 6's mistake.** `ga4_team` got engaged sessions right (106,301) because `sql_reviewer` sent the first query back.
2. **The pipeline lost a step's knowledge.** In `q14`, `ga4_flow` returned regions (correct) but didn't explain **why**: `answer_writer` only sees the SQL and the verdict, not the privacy rule, so it couldn't say "cities are tier C3". The `ga4_team` analyst had the skill and explained it. In a pipeline, **each step knows only what you pass to it**. Fix (try it): give `answer_writer` the skill, or have `sql_writer` also save a short note of the rules it applied.
3. **Small steps use fewer tokens.** `ga4_flow` used the fewest tokens and cost the least, even with more model calls: each call carries a short instruction and few tools. `ga4_guide` carries everything on every call.
4. **One run each.** Lesson 4 showed that one run can mislead; a difference of one case is within noise. Run with `--num_runs 3` before deciding anything.

## Step 6. Commit

```bash
git status --short
git add agents/ga4_team agents/ga4_flow && git commit -m "Lesson 7: ga4_team (routing, agent as tool) and ga4_flow (workflow with review loop)"
```

## When to use which

| | One agent | Team with transfer (`ga4_team`) | Workflow (`ga4_flow`) |
|---|---|---|---|
| Who decides the next step | the model | the model | **your code** |
| Good for | small jobs | conversations that change topic | a process that must happen in order: write, review, then run |
| Guarantee | none | none: the model can skip the reviewer | **the reviewer always runs**, and SQL only runs after it |
| Cost | lowest | more calls; each transfer resends the prompt | more calls, but each one is small |
| Debugging | one long trace | follow the transfers | follow the nodes and routes |

The key difference: in `ga4_team` the instruction **asks** the analyst to call the reviewer. In `ga4_flow` the graph **makes** it happen. When a step must not be skipped, put it in the graph, not in a prompt. (Lessons 9 and 11 take the same idea further, with guardrails in code and on the network.)

## Check yourself

1. What's the difference between transferring to a sub-agent and calling an agent as a tool?
2. In `ga4_team`, what does the front desk read to decide where a message goes?
3. In `ga4_flow`, how does `sql_writer` learn what the reviewer said?
4. Why is `check_review` plain Python instead of an agent?
5. Why does `start_question` reset `review` and `tries`?
6. Which team **guarantees** that the SQL is reviewed before it runs, and why?
7. Why did we use `Workflow` instead of `SequentialAgent` and `LoopAgent`?

## Send me back

- Part A: the authors and transfers you saw for the two messages
- Part B: whether the reviewer sent the engaged-sessions query back, and the final number
- Part C: the pass counts for both teams
- Anything that didn't match this page

Next, lesson 8: **deploy** to Agent Runtime, which creates cloud resources, so we'll go through the plan and cost before running anything.
