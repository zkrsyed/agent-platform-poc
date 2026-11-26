"""ga4_guide, lesson 4 version.

Lesson 3 added Knowledge Catalog (MCP) and BigQuery. Now the business rules also come from
a skill, loaded only when needed, and the catalog is used only for what the skill lacks.
"""

import os
from pathlib import Path

import google.auth
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.integrations.bigquery import BigQueryCredentialsConfig, BigQueryToolset
from google.adk.integrations.bigquery.config import BigQueryToolConfig, WriteMode
from google.adk.skills import load_skill_from_dir  # NEW
from google.adk.tools import ToolContext
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.adk.tools.skill_toolset import SkillToolset  # NEW
from google.auth.transport.requests import Request

from .guardrails import GuardrailsPlugin  # lesson 9


PROJECT = "kc-okf-poc-261122"
# Lesson 8: gemini-3.5-flash is served only from the "global" location, but a deployed agent runs in a
# region (us-central1), so we pin the model's location here instead of relying on GOOGLE_CLOUD_LOCATION.
MODEL = Gemini(model="gemini-3.5-flash", client_kwargs={"enterprise": True, "location": "global"})

_HERE = Path(__file__).resolve().parent
# Lesson 8: a deployed copy carries the skill inside its own folder; locally it's in repo_root/skills.
SKILL_DIR = next(
    d for d in (_HERE / "skills" / "ga4-context", _HERE.parents[1] / "skills" / "ga4-context") if d.is_dir()
)

# Lesson 9: deployed, the agent's token only works on Google's mTLS hosts (*.mtls.googleapis.com);
# the plain host answered 401. The build's .env sets the mTLS URL; locally we use the plain one.
CATALOG_MCP_URL = os.environ.get("CATALOG_MCP_URL", "https://dataplex.googleapis.com/mcp")

_creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])


def _catalog_headers(_context) -> dict[str, str]:
    """Runs before every MCP call, so the token never goes stale (they last about an hour)."""
    if not _creds.valid:
        _creds.refresh(Request())
    return {"Authorization": f"Bearer {_creds.token}", "x-goog-user-project": PROJECT}


catalog = McpToolset(
    connection_params=StreamableHTTPConnectionParams(url=CATALOG_MCP_URL),
    header_provider=_catalog_headers,
    tool_filter=["search_entries", "lookup_context", "lookup_entry"],
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

# NEW: the skill. We hide run_skill_script: a skill could carry code, and we don't need it.
skills = SkillToolset(
    skills=[load_skill_from_dir(SKILL_DIR)],
    tool_filter=["list_skills", "load_skill", "load_skill_resource"],
)


def remember_analyst(name: str, team: str, tool_context: ToolContext) -> dict:
    """Remember who the analyst is, so later answers can address them by name.

    Call this once, as soon as the analyst tells you their name and team.

    Args:
        name: The analyst's first name.
        team: The team the analyst works in.
    """
    tool_context.state["user:analyst_name"] = name
    tool_context.state["user:team"] = team
    tool_context.state["times_remembered"] = tool_context.state.get("times_remembered", 0) + 1
    return {"status": "saved", "name": name, "team": team}


root_agent = Agent(
    name="ga4_guide",
    model=MODEL,
    description=(
        "Answers questions about the GA4 sample table "
        "kc-okf-poc-261122.ga4_sample.events (Google Merchandise Store)."
    ),
    instruction="""You are the GA4 data guide for the BigQuery table
`kc-okf-poc-261122.ga4_sample.events` (Google Merchandise Store, 2020-11-01 to 2021-01-31).

The analyst you are talking to: {user:analyst_name?} (team: {user:team?}).
If the name above is empty, ask for their name and team once, then call `remember_analyst`.

How to answer a data question:
1. Load the skill `ga4-context` (`load_skill`) before writing any SQL, and follow its rules.
   Read a reference file (`load_skill_resource`) only when the question needs it: revenue per
   day, sessions, conversion, buyers.
2. Use the Knowledge Catalog (`lookup_context`, or `search_entries` if unsure of the name) only
   when you need a column or type that the skill does not give you.
3. Write ONE read-only SQL query and run it with `execute_sql`.
4. Answer in a few sentences, give the number, show the SQL you ran, and mention any rule that
   changed the answer (for example, that the last 3 days were left out).
If a tool fails, say what failed. Never invent figures.""",
    tools=[remember_analyst, catalog, bigquery, skills],  # NEW: the skill toolset joins the list
    output_key="last_answer",
)

# Lesson 9: an App wraps the agent and adds plugins that run around every call.
# adk web and adk deploy look for `app` first, then `root_agent`.
app = App(name="ga4_guide", root_agent=root_agent, plugins=[GuardrailsPlugin()])
