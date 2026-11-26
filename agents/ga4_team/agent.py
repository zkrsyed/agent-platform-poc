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
