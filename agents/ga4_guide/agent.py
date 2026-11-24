"""ga4_guide, lesson 2 version.

No data or catalog access yet. This version only shows the shape of an ADK agent:
instruction + one tool + state.
"""

from google.adk.agents import Agent
from google.adk.tools import ToolContext

MODEL = "gemini-3.5-flash"


def remember_analyst(name: str, team: str, tool_context: ToolContext) -> dict:
    """Remember who the analyst is, so later answers can address them by name.

    Call this once, as soon as the analyst tells you their name and team.

    Args:
        name: The analyst's first name.
        team: The team the analyst works in.
    """
    # "user:" prefix = kept for this user across ALL their sessions.
    tool_context.state["user:analyst_name"] = name
    tool_context.state["user:team"] = team
    # No prefix = kept only in THIS session.
    tool_context.state["times_remembered"] = tool_context.state.get("times_remembered", 0) + 1
    return {"status": "saved", "name": name, "team": team}


root_agent = Agent(
    name="ga4_guide",
    model=MODEL,
    # The description is for OTHER agents and registries (lessons 10 and 12), not for this model.
    description=(
        "Answers questions about the GA4 sample table "
        "kc-okf-poc-261122.ga4_sample.events (Google Merchandise Store)."
    ),
    instruction="""You are the GA4 data guide for the BigQuery table
`kc-okf-poc-261122.ga4_sample.events` (Google Merchandise Store, 2020-11-01 to 2021-01-31).

The analyst you are talking to: {user:analyst_name?} (team: {user:team?}).
If the name above is empty, ask for their name and team once, then call `remember_analyst`.

Right now you have NO access to the data or the data catalog.
When asked for numbers, say so plainly and say what access you would need. Never invent figures.
Keep answers to a few sentences.""",
    tools=[remember_analyst],
    # Copies the agent's final reply into session state under this key.
    output_key="last_answer",
)
