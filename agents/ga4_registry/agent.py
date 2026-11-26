"""ga4_registry (lesson 10): ga4_guide's skill and catalog tools, found in Agent Registry instead of hard-coded.

- The skill comes from the registry: SkillToolset(registry=GCPSkillRegistry(...)) gives the agent a
  `search_skills` tool, and `load_skill` downloads a registry skill by name. No skill folder here.
- The catalog MCP server comes from the registry too: we look it up by its display name, and the
  registry supplies its address and auth. No "https://dataplex.googleapis.com/mcp" in this file.
"""

from google.adk.agents import Agent
from google.adk.integrations.agent_registry import AgentRegistry
from google.adk.integrations.skill_registry import GCPSkillRegistry
from google.adk.models import Gemini
from google.adk.tools.skill_toolset import SkillToolset

PROJECT = "kc-okf-poc-261122"
MODEL = Gemini(model="gemini-3.5-flash", client_kwargs={"enterprise": True, "location": "global"})


def registry_mcp_toolset(display_name: str, tool_filter: list[str]):
    """Find an MCP server in Agent Registry by its display name and connect to it."""
    registry = AgentRegistry(project_id=PROJECT, location="global")
    for server in registry.list_mcp_servers().get("mcpServers", []):
        if server.get("displayName") == display_name:
            toolset = registry.get_mcp_toolset(server["name"])
            toolset.tool_filter = tool_filter  # the server offers ~20 tools, some that write: keep 3 readers
            return toolset
    raise LookupError(f"No MCP server named {display_name!r} in Agent Registry")


skills = SkillToolset(
    registry=GCPSkillRegistry(project_id=PROJECT, location="global"),
    tool_filter=["search_skills", "load_skill", "load_skill_resource"],
)
catalog = registry_mcp_toolset("dataplex.googleapis.com", ["search_entries", "lookup_context", "lookup_entry"])

root_agent = Agent(
    name="ga4_registry",
    model=MODEL,
    description="Explains the rules for the GA4 table, using a skill and catalog tools found in Agent Registry.",
    instruction="""You explain the data team's rules for the BigQuery table
`kc-okf-poc-261122.ga4_sample.events`. You have no skill folder of your own: first call
`search_skills` to find the right skill in the registry, then `load_skill` with the name it returns,
and answer from it. Use the catalog tools only if the skill doesn't cover the question.
Say which skill (and catalog entry) each answer came from. Never invent rules.""",
    tools=[skills, catalog],
)
