"""ga4_a2a (lesson 12): the lesson 7 analyst, with its reviewer in ANOTHER process.

    lesson 7:  data_analyst --AgentTool--> sql_reviewer          (same process, a function call)
    lesson 12: ga4_a2a      --AgentTool--> RemoteA2aAgent ==A2A==> sql_reviewer server (port 8001)

The analyst's code only knows the reviewer's agent card URL. Swap the URL and the reviewer can
run anywhere (another team, Agent Runtime, another company), in any framework that speaks A2A.
"""

import os
from pathlib import Path

import google.auth
from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.integrations.bigquery import BigQueryCredentialsConfig, BigQueryToolset
from google.adk.integrations.bigquery.config import BigQueryToolConfig, WriteMode
from google.adk.skills import load_skill_from_dir
from google.adk.tools import AgentTool
from google.adk.tools.skill_toolset import SkillToolset

PROJECT = "kc-okf-poc-261122"
MODEL = "gemini-3.5-flash"
SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "ga4-context"
REVIEWER_CARD = os.environ.get("REVIEWER_CARD_URL", "http://localhost:8001/.well-known/agent-card.json")

_creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])

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

# The remote reviewer: ADK reads its agent card from the URL, then sends it A2A messages.
sql_reviewer = RemoteA2aAgent(
    name="sql_reviewer",
    agent_card=REVIEWER_CARD,
    description="Reviews a BigQuery SQL query for the GA4 table against the data team's rules. "
    "Send it the analyst's question and the SQL. It replies APPROVED or lists the problems.",
)

root_agent = Agent(
    name="ga4_a2a",
    model=MODEL,
    description="Answers GA4 data questions with SQL, after a remote reviewer approves the query.",
    instruction="""You answer data questions about `kc-okf-poc-261122.ga4_sample.events`.
1. Load the skill `ga4-context` and the reference file the question needs. Use `get_table_info`
   only if you need a column.
2. Write ONE read-only SQL query. Before running it, call `sql_reviewer` with the question and
   the SQL. If it does not reply APPROVED, fix the SQL and ask again (at most 2 times).
3. Run the approved SQL with `execute_sql` and answer in a few sentences: the number, the SQL,
   and any rule that changed the answer. Never invent figures.""",
    tools=[
        SkillToolset(
            skills=[load_skill_from_dir(SKILL_DIR)],
            tool_filter=["list_skills", "load_skill", "load_skill_resource"],
        ),
        bigquery,
        AgentTool(agent=sql_reviewer),
    ],
)
