"""ga4_guide, lesson 3 version.

Lesson 2 had no data access. Now it can read the table's real schema from Knowledge
Catalog (hosted MCP server) and run read-only SQL on BigQuery.
"""

import google.auth
from google.adk.agents import Agent
from google.adk.integrations.bigquery import BigQueryCredentialsConfig, BigQueryToolset
from google.adk.integrations.bigquery.config import BigQueryToolConfig, WriteMode
from google.adk.tools import ToolContext
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.auth.transport.requests import Request

PROJECT = "kc-okf-poc-261122"
MODEL = "gemini-3.5-flash"

# NEW: your ADC login. Locally this is you; on Agent Runtime (lesson 8) it will be the agent identity.
_creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])


def _catalog_headers(_context) -> dict[str, str]:
    """NEW: runs before every MCP call, so the token never goes stale (they last about an hour)."""
    if not _creds.valid:
        _creds.refresh(Request())
    return {"Authorization": f"Bearer {_creds.token}", "x-goog-user-project": PROJECT}


# NEW: Google's hosted Knowledge Catalog MCP server, read tools only.
catalog = McpToolset(
    connection_params=StreamableHTTPConnectionParams(url="https://dataplex.googleapis.com/mcp"),
    header_provider=_catalog_headers,
    tool_filter=["search_entries", "lookup_context", "lookup_entry"],
)

# NEW: BigQuery, read-only, capped at 1 GB per query.
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
1. Look up the table in the Knowledge Catalog first (`lookup_context`, or `search_entries` if you
   are unsure of the name). Use the real column names and notes you find there. Never guess columns.
2. Write ONE read-only SQL query and run it with `execute_sql`. Follow any rules the catalog gives
   you about partition filters.
3. Answer in a few sentences, give the number, and show the SQL you ran.
If a tool fails, say what failed. Never invent figures.""",
    tools=[remember_analyst, catalog, bigquery],  # NEW: two toolsets next to the function tool
    output_key="last_answer",
)
