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
