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
