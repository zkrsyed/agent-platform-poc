# Lesson 3: Real tools: Google's Knowledge Catalog MCP server and BigQuery

**Goal:** give `ga4_guide` two real sets of tools. One is **Google's hosted Knowledge Catalog MCP server**, so it can read the table's real schema instead of guessing. The other is the **BigQuery toolset**, so it can run the SQL. Then ask the same December-2020 question as in Lesson 2 and compare. About 40 minutes.

**Cost:** a few Gemini calls plus BigQuery queries. The answer query reads about 34 MB (**verified** with a free dry run), which is roughly $0.0002. We also set a hard cap, so no single query can read more than 1 GB. Nothing is created in GCP.

## The ideas

| Idea | One line | .NET comparison |
|---|---|---|
| **Function tool** | A Python function ADK wraps (`remember_analyst`, lesson 2) | A method you register as a handler |
| **Toolset** | An object that *produces a list* of tools when the agent starts: `McpToolset`, `BigQueryToolset` | A DI module that registers many services at once |
| **MCP (Model Context Protocol)** | A standard way for a server to publish tools to any agent | OpenAPI/Swagger, but built for agents |
| **MCP client / server** | The agent side asks "what tools do you have?" (`tools/list`) and calls them (`tools/call`) | `HttpClient` against a Web API |
| **Streamable HTTP** | How a *remote* MCP server is reached: one HTTPS URL | A normal REST endpoint |
| **`tool_filter`** | A list of tool names the agent may see. The rest are hidden from it | A whitelist of controller actions |
| **`header_provider`** | A function that returns fresh HTTP headers (our token) on every call | A `DelegatingHandler` that adds a bearer token |
| **Grounding** | Making the model answer from real data instead of memory | Reading from the database instead of guessing |

**Why `tool_filter` matters here:** Google's hosted server offers **15 tools** (**verified** on 2026-11-25 with the script in Step 1). Some of them *change* the catalog or its permissions. If you hand all of them to an agent, the agent can use all of them. We only give it the read tools. Lessons 9 and 11 add guardrails on top of this.

## What you'll have at the end

```
scripts/
  list_mcp_tools.py   ← new: asks the hosted server what it offers
agents/ga4_guide/
  agent.py            ← changed: + McpToolset (catalog) + BigQueryToolset (SQL)
```

---

## Step 1. Ask Google's MCP server what it offers

`McpToolset` does this on every startup. Do it by hand once, so MCP stops being magic. Create **`scripts/list_mcp_tools.py`**:

```python
"""List the tools on Google's hosted Knowledge Catalog MCP server (read-only, free)."""

import asyncio

import google.auth
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.auth.transport.requests import Request

PROJECT = "kc-okf-poc-261122"
MCP_URL = "https://dataplex.googleapis.com/mcp"  # Knowledge Catalog's old name is Dataplex


async def main() -> None:
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())  # turns your ADC login into a short-lived access token
    toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=MCP_URL,
            headers={"Authorization": f"Bearer {creds.token}", "x-goog-user-project": PROJECT},
        )
    )
    try:
        for tool in await toolset.get_tools():
            print(f"{tool.name:28} {(tool.description or '')[:80]!r}")
    finally:
        await toolset.close()


asyncio.run(main())
```

```bash
cd ~/apps/agent-platform-poc && export CLOUDSDK_ACTIVE_CONFIG_NAME=kc-okf
```

```bash
uv run python scripts/list_mcp_tools.py
```

**Look for** 15 tools. Sorted by what they do (the grouping is **our reading of the names and descriptions**; check the descriptions yourself):

| Read (we allow) | Change something (we hide) |
|---|---|
| `search_entries`, `lookup_context`, `lookup_entry`, `lookup_entry_links`, `list_entries`, `get_glossary`, `get_operation`, `get_entry_group_iam_policy` | `create_entry_group`, `update_entry_group`, `delete_entry`, `delete_entry_link`, `upsert_entry`, `upsert_entry_link`, `set_entry_group_iam_policy` |

- **Authentication** is a normal Google access token in a `Bearer` header. It's your ADC login now; in lesson 9 it will be the agent's own identity.
- It worked without any extra setup in `kc-okf` (**verified**). The docs say the caller needs the role `roles/mcp.toolUser` (**docs**; your account was allowed, so either you already hold it or your project owner role covers it, **guess**).
- `search_entries` takes `query`, `projectId`, `location`, `scopeType`, `scopeId`, `pageSize`, `pageToken`. `lookup_context` takes `projectId`, `location` and `resources`, and it's described as "designed to be called after `SearchEntries`" and returns "LLM-ready" YAML with the schema, quality and usage statistics (**verified**, from the tool descriptions).
- The lesson 1 `mcp` package (version 2.x) renamed its low-level client function. That's why we go through ADK's `McpToolset`, which hides it.

## Step 2. Know what BigQuery's toolset offers

ADK ships its own BigQuery tools. You don't write MCP for them; they're Python functions in `google.adk.integrations.bigquery` (**verified**). The toolset offers 11:

`get_dataset_info`, `get_table_info`, `list_dataset_ids`, `list_table_ids`, `get_job_info`, **`execute_sql`**, `forecast`, `analyze_contribution`, `detect_anomalies`, `ask_data_insights`, `search_catalog`.

We only use **`execute_sql`** (run a query) and **`get_table_info`** (read a table's schema). Three safety settings, all in `BigQueryToolConfig`:

| Setting | Our value | Why |
|---|---|---|
| `write_mode` | `BLOCKED` | The default: only `SELECT` is allowed. No `INSERT`, `DELETE`, `DROP` |
| `maximum_bytes_billed` | `1_000_000_000` (1 GB) | A query that would read more is rejected before it runs. The whole table is 3.6 GB, so a careless `SELECT *` fails. The December purchase count reads about 34 MB |
| `max_query_result_rows` | `50` | Stops a huge result from flooding the model's context |

> **There's a hosted BigQuery MCP server too** (**verified** 2026-11-25): `https://bigquery.googleapis.com/mcp` lists 9 tools (`execute_sql`, `execute_sql_readonly`, `get_table_info`, `list_dataset_ids`, `list_table_ids`, `get_dataset_info`, `get_job`, `get_query_results`, `cancel_job`). We use the ADK library here because its safety settings are easy to see. Lesson 11 switches to the hosted one: calls to an MCP server cross the network, so Agent Gateway can govern them (**docs**); a function inside your program can't be.

## Step 3. Update `agent.py`

Replace **`agents/ga4_guide/agent.py`** with this. New parts are marked `# NEW`:

```python
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
```

**Read it before running:**
- `tools=[...]` now mixes a **function** (`remember_analyst`) and two **toolsets**. ADK flattens them into one list the model sees.
- `McpToolset(... tool_filter=[3 names])` means the agent never even learns the other 12 tools exist.
- The **instruction** tells the model *how to work*: catalog first, then SQL. Nothing forces that order; it's only text. Whether the model follows it is exactly what Langfuse will show you.
- `_catalog_headers` is a `header_provider`. ADK calls it before each MCP request. Without it the token would expire after about an hour and every call would fail with `401`.
- `compute_project_id=PROJECT` makes BigQuery bill and run in `kc-okf` only. The agent can't send a query to another project.

## Step 4. Chat with it

```bash
./scripts/adk.sh web agents
```

(Always start through `scripts/adk.sh`, from lesson 2: it loads the Langfuse settings. A plain `uv run adk web agents` sends **no** traces.)

Open the page (same SSH tunnel as lesson 2 if you're on another computer). Pick **ga4_guide**, start a **new session**, and ask:

1. `Hi, I'm Priya from merch analytics.` (You'll see the name tool still works.)
2. `How many purchases were there in December 2020?`

**Look for** in the **Events** tab, in order:
- a call to `lookup_context` (or `search_entries` first, then `lookup_context`)
- a call to `execute_sql`, with SQL that filters on **`event_date_dt`** and **not** on `_TABLE_SUFFIX`
- the final answer with a number and the SQL shown

In Lesson 2 the same question got "I can't access the data" and a **wrong** `_TABLE_SUFFIX` guess. Whether the catalog fixes that is the point of this lesson. **Don't assume it will**; check what the SQL really says.

Try two more:
3. `Which columns does the events table have for ecommerce revenue?`
4. `Delete the entry for the events table from the catalog.` The agent has no such tool. **Look for** how it says no. This is the cheapest guardrail there is: a tool it was never given.

## Step 5. See it in Langfuse

As long as you started through `scripts/adk.sh`, the traces are going there. Open **Observations**, or the newest trace, and click the rows:
- The **MCP calls** show as TOOL spans (`lookup_context`, ...). Click one: its **Input** is what the model asked for, its **Output** is what Google's server returned (the schema, as YAML).
- The `execute_sql` span shows the exact SQL and the rows that came back.
- The model-call rows show **how the prompt grew**: the tool results are now part of the next call's input, and the token count jumps.

**Check:** how many Gemini calls did one question take, and how many tokens? Write the numbers down. They go into results, and lesson 7 compares them with a multi-agent version.

## Step 6. Check the number yourself

Never trust an agent's number without one independent check:

```bash
bq query --use_legacy_sql=false "SELECT COUNT(*) AS purchases FROM \`kc-okf-poc-261122.ga4_sample.events\` WHERE event_name = 'purchase' AND event_date_dt BETWEEN '2020-12-01' AND '2020-12-31'"
```

This reads about 34 MB. **Look for:** the same number the agent gave. If they differ, compare the two SQL statements: that difference is a finding.

## Step 7. Commit

```bash
git status --short
```

**Look for:** `agent.py` and `__init__.py` modified, `scripts/list_mcp_tools.py` and `scripts/adk.sh` new, and **no** `.env`.

```bash
git add agents/ga4_guide/agent.py agents/ga4_guide/__init__.py scripts/list_mcp_tools.py scripts/adk.sh scripts/runner_demo.py && git commit -m "Lesson 3: Knowledge Catalog MCP + BigQuery tools"
```

---

## Check yourself

1. What is the difference between a function tool, a toolset and an MCP server?
2. The hosted server has 15 tools; we allow 3. Where is that decided, and who can change it? (Compare with lesson 11.)
3. Why does the catalog client use a `header_provider` instead of a fixed `headers=` value?
4. Which three settings keep BigQuery safe, and which one stops an expensive query before it runs?
5. In Langfuse, how can you tell that the agent used the catalog *before* it wrote SQL?

## Send me back

- A screenshot of the **Events** tab (or the Langfuse trace) for the December question
- The agent's number, and the number from Step 6
- The SQL the agent ran: did it use `event_date_dt`?
- Any tool errors (a `403` or `401` here is a finding, not a failure)

Next, lesson 4: a **skill**. The catalog may already tell the agent the table's columns, but business rules (*"never output city-level data"*, *"revenue means this field"*) belong in a skill.
