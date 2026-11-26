"""Write build/okf_toolspec.json: our MCP server's tool list, in the form Agent Registry wants (lesson 10).

  uv run python scripts/mcp_toolspec.py

It starts our lesson 5 server over stdio (no network, no cloud), asks for its tools (`tools/list`),
and saves {"tools": [{name, description, inputSchema}, ...]}: the "tool spec" the registry shows
to anyone who finds the server there.
"""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "mcp_servers" / "okf" / "server.py"
OUT = ROOT / "build" / "okf_toolspec.json"


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
    spec = {"tools": [
        {"name": t.name, "description": t.description or "", "inputSchema": t.input_schema} for t in tools
    ]}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(spec, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(tools)} tools ({', '.join(t.name for t in tools)}), "
          f"{OUT.stat().st_size} bytes (limit 150 KB)")


asyncio.run(main())
