"""Talk to our own OKF MCP server, over stdio or over HTTP. Free: no Gemini calls.

  uv run python scripts/list_okf_tools.py stdio    # starts the server as a child process
  uv run python scripts/list_okf_tools.py http     # connects to a server you started yourself on port 8808
"""

import asyncio
import sys
from pathlib import Path

from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams, StreamableHTTPConnectionParams
from mcp import StdioServerParameters

SERVER = Path(__file__).resolve().parents[1] / "mcp_servers" / "okf" / "server.py"


def make_toolset(mode: str) -> McpToolset:
    if mode == "stdio":
        params = StdioConnectionParams(
            server_params=StdioServerParameters(command=sys.executable, args=[str(SERVER)]),
        )
    else:
        params = StreamableHTTPConnectionParams(url="http://127.0.0.1:8808/mcp")
    return McpToolset(connection_params=params)


def show(result: dict) -> None:
    """Print what came back: the parts of the result, then the text inside each part."""
    print("result parts:", list(result))  # e.g. ['content', 'isError'] (Step 5 adds 'structuredContent')
    for part in result.get("content", []):
        print(part["text"])


async def main(mode: str) -> None:
    toolset = make_toolset(mode)
    try:
        tools = {t.name: t for t in await toolset.get_tools()}
        for name, tool in tools.items():
            print(f"{name:14} {(tool.description or '').splitlines()[0]}")
        print("\nlist_pages ->")
        show(await tools["list_pages"].run_async(args={}, tool_context=None))
        print("\nsearch_pages('72') ->")
        show(await tools["search_pages"].run_async(args={"query": "72", "max_results": 2}, tool_context=None))
    finally:
        await toolset.close()


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "stdio"))