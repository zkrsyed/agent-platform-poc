"""okf_guide: a small agent with ONE toolset, our own OKF MCP server.

It has no BigQuery, no catalog and no skill folder. Everything it knows about the table's rules
it fetches by page name from the server we built in lesson 5, which reads Knowledge Catalog
live (start the server first).
"""

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

okf = McpToolset(
    connection_params=StreamableHTTPConnectionParams(url="http://127.0.0.1:8808/mcp"),
    tool_filter=["list_pages", "get_page", "search_pages"],
)

root_agent = Agent(
    name="okf_guide",
    model="gemini-3.5-flash",
    description="Answers questions about the GA4 table's rules, using our catalog pages server.",
    instruction="""You answer questions about the rules for the GA4 merchandise-store table.
Use only the catalog pages server: call `list_pages`, then `get_page` for the page you need
(or `search_pages` for a quick look). For every rule you state, name the page it came from.
If the pages do not say, say so. Never invent rules.""",
    tools=[okf],
)
