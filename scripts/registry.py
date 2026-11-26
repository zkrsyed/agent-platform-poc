"""Look things up in Agent Registry with ADK's client (lesson 10). Reads only.

  uv run python scripts/registry.py agents [LOCATION]        # agents (ours is auto-registered)
  uv run python scripts/registry.py mcp    [LOCATION]        # MCP servers (Google's + ours)
  uv run python scripts/registry.py show   NAME              # everything the registry knows about one entry
  uv run python scripts/registry.py tools  NAME              # connect to a registered MCP server and list its tools

LOCATION defaults to "global". NAME is either the full resource name that `agents` or `mcp` printed,
or just the display name (for example ga4-guide), which is looked up in global and us-central1.
"""

import asyncio
import json
import sys

from google.adk.integrations.agent_registry import AgentRegistry

PROJECT = "kc-okf-poc-261122"


def registry(location: str = "global") -> AgentRegistry:
    return AgentRegistry(project_id=PROJECT, location=location)


def show_list(kind: str, location: str) -> None:
    reg = registry(location)
    data = reg.list_agents() if kind == "agents" else reg.list_mcp_servers()
    items = data.get("agents" if kind == "agents" else "mcpServers", [])
    print(f"{len(items)} {kind} in {location}")
    for item in items:
        print(f"- {item.get('displayName', '?')}\n    {item['name']}")


def resolve(name: str) -> str:
    """Accept a display name like "ga4-guide" as well as a full resource name."""
    if name.startswith("projects/"):
        return name
    for location in ("global", "us-central1"):
        reg = registry(location)
        for kind, key in (("agents", "agents"), ("mcp", "mcpServers")):
            data = reg.list_agents() if kind == "agents" else reg.list_mcp_servers()
            for item in data.get(key, []):
                if item.get("displayName", "").lower() == name.lower():
                    return item["name"]
    sys.exit(f"No agent or MCP server named {name!r} in global or us-central1. "
             "Run `agents` or `mcp` to see the names.")


def show(name: str) -> None:
    name = resolve(name)
    location = name.split("/locations/")[1].split("/")[0]
    reg = registry(location)
    info = reg.get_agent_info(name) if "/agents/" in name else reg.get_mcp_server(name)
    print(json.dumps(info, indent=2)[:4000])


async def tools(name: str) -> None:
    name = resolve(name)
    location = name.split("/locations/")[1].split("/")[0]
    toolset = registry(location).get_mcp_toolset(name)  # URL and auth come from the registry, not our code
    try:
        for tool in await toolset.get_tools():
            print(f"- {tool.name}: {(tool.description or '').splitlines()[0][:90]}")
    finally:
        await toolset.close()


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command in ("agents", "mcp"):
        show_list(command, sys.argv[2] if len(sys.argv) > 2 else "global")
    elif command == "show":
        show(sys.argv[2])
    elif command == "tools":
        asyncio.run(tools(sys.argv[2]))
    else:
        sys.exit(__doc__)
