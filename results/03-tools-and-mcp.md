# Lesson 3 results: Knowledge Catalog MCP + BigQuery tools

Run on 2026-11-25. Everything on this page is **verified** unless marked otherwise. **Status: done.**

## What worked

| Step | Result |
|---|---|
| 1. `list_mcp_tools.py` | `https://dataplex.googleapis.com/mcp` answered with our ADC token: **15 tools**. 8 read-style (`search_entries`, `lookup_context`, `lookup_entry`, `lookup_entry_links`, `list_entries`, `get_glossary`, `get_operation`, `get_entry_group_iam_policy`) and 7 that change things (`create_entry_group`, `update_entry_group`, `upsert_entry`, `upsert_entry_link`, `delete_entry`, `delete_entry_link`, `set_entry_group_iam_policy`). No extra role or setup was needed in `kc-okf` |
| 3. New `agent.py` | The model sees 6 tools: `remember_analyst`, `search_entries`, `lookup_context`, `lookup_entry`, `get_table_info`, `execute_sql`. The other 12 catalog tools and 9 BigQuery tools are not shown to it |
| 4. December question in `adk web` | `search_entries` → `lookup_context` → `execute_sql` → **2,434 purchases**, with SQL filtered on `event_date_dt` (lesson 2 guessed `_TABLE_SUFFIX`) |
| 6. Independent check with `bq query` | **2,434**. Same number |
| Delete request in `adk run` | "I cannot delete the entry for the `events` table… my tools are limited to looking up entries, searching, and running read-only SQL." No tool was called (checked in Langfuse): the missing tool is the guardrail |
| Ecommerce-columns question in `adk run` | Listed the `ecommerce.*` revenue columns and quoted an "Official Metric Rule" (MSC-417: report financial figures with the `_in_usd` columns). That rule is **inside the catalog's context for the table** (found in the `lookup_context` output) |

## The trace of one data question (Langfuse, 20:21 local)

| # | Step | Input tokens | Note |
|---|---|---|---|
| 1 | Model → `remember_analyst` | 8,977 | A fresh session already starts at about 9,000 tokens: instruction + 6 tool descriptions |
| 2 | Model → `search_entries` (query `system=BIGQUERY ga4_sample.events`) | 9,228 | Returned 2 entries: the table and its dataset, with their long catalog addresses (project **number**, not name) |
| 3 | Model → `lookup_context` | 10,765 | This model call took **18.3 s** (cause unknown, **guess**: throttling or a slow response) |
| 4 | Model → `execute_sql` | **31,462** | The `lookup_context` result (about 35,500 characters of YAML) is now part of the conversation |
| 5 | Model writes the answer | 31,923 | |

Total: 5 model calls, 4 tool calls, **30.8 s**, about **$0.10** (Langfuse's own estimate from the model name and tokens; the price rates are a **guess**).

## Findings

1. **Search, then look up, then run.** `search_entries` finds the table's catalog address, `lookup_context` reads about it, `execute_sql` runs the query. The model chose this order from our instruction; nothing forces it.
2. **The catalog fixed the schema guessing.** `lookup_context` describes `event_date_dt` as the date field for "date-partitioned analysis", and the SQL used it.
3. **Tool results stay in the conversation.** The big `lookup_context` result is sent again on every later model call. Even a plain "Hey" in the same session cost **32,767 input tokens** (`adk web` replays the saved session from `.adk/session.db`). This is the main cost of grounding with a large tool result; lessons 4 and 7 can reduce it.
4. **The agent started catalog lookups on "Hi"**, before any data question. The instruction says "look up the table first" and the model did it early.
5. **MCP spans:** `MCP send initialize` and `MCP send tools/list` (about 0.2 s together) appear at the start of **every turn**: the client reconnects and re-reads the menu. Their Input/Output are empty (protocol plumbing); the content is on the tool and model rows.
6. **A search returns both table and dataset.** With many similar tables, the agent would have to choose; our instruction doesn't tell it to ask when unsure (**guess** that it would pick one silently).
7. **`mcp` 2.x renamed its low-level client function** (`streamablehttp_client` → `streamable_http_client`), so we go through ADK's `McpToolset`.
8. **Google also hosts a BigQuery MCP server** (`https://bigquery.googleapis.com/mcp`, 9 tools). Lesson 11 swaps to it so Agent Gateway can govern the SQL calls (**docs**).

9. **The catalog result is sent twice.** The `lookup_context` tool result has `content[0].text` (36,768 characters) and `structuredContent` (36,744 characters): the same text, and both go to the model (the message is about 75,000 characters). Stripping one copy would roughly halve that message (**guess**; lesson 9's plugin can try).

## Tracing fixes found along the way (applies to every lesson from now on)

- **`adk web` reads the tracing settings at startup, from the shell**, not from `agents/ga4_guide/.env`. Started plainly it sent nothing; sessions run before the restart are not in Langfuse.
- **`adk run` has no tracing setup at all** in ADK 2.15's `cli.py`.
- Fix: `agents/ga4_guide/__init__.py` sets up tracing on import (guarded, so it doesn't fight `adk web`'s own), and `scripts/adk.sh` loads `.env` before running any `adk` command. Tested: `adk run` through the wrapper produced a trace; `adk web` through the wrapper had the variables and its requests arrived.
- `runner_demo.py` no longer sets up tracing itself.
- Port 8123 on this server is Home Assistant; test servers use another port.

## Cost

A few cents of Gemini per question and about $0.0002 of BigQuery (34 MB). The `maximum_bytes_billed` cap of 1 GB was never reached.
