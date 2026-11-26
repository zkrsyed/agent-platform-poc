"""Look at the two other things an MCP server can offer besides tools: resources and prompts. Free."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mcp_servers.okf.server import mcp  # importing it does not start the server


async def main() -> None:
    print("resource templates:", [t.uri_template for t in await mcp.list_resource_templates()])
    parts = await mcp.read_resource("okf://pages/documents~playbook-final-daily-net-revenue")
    print("resource text starts:", parts[0].content[:60].replace("\n", " "), "...")
    print("prompts:", [p.name for p in await mcp.list_prompts()])
    prompt = await mcp.get_prompt("answer_from_pages", {"question": "Why drop the last 3 days?"})
    print("prompt text:", prompt.messages[0].content.text[:120].replace("\n", " "), "...")


asyncio.run(main())
