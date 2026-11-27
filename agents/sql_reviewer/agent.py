"""sql_reviewer (lesson 12): lesson 7's reviewer, moved out of ga4_team into its own agent.

It no longer lives inside the analyst's process. `a2a_app.py` serves it over A2A, and other
agents reach it by URL, through its agent card. It has the skill, no BigQuery and no catalog:
it only reads SQL text and says APPROVED or lists the problems.
"""

from pathlib import Path

from google.adk.agents import Agent
from google.adk.skills import load_skill_from_dir
from google.adk.tools.skill_toolset import SkillToolset

MODEL = "gemini-3.5-flash"
SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "ga4-context"

root_agent = Agent(
    name="sql_reviewer",
    model=MODEL,
    description="Reviews a BigQuery SQL query for the GA4 table against the data team's rules. "
    "Send it the analyst's question and the SQL. It replies APPROVED or lists the problems.",
    instruction="""You review a SQL query against the rules in the skill `ga4-context` (load it,
and the reference file the question needs). You do not run queries. The request contains the
analyst's question and the SQL.

Be strict. Check, one by one:
- every numbered rule in the skill that applies to this question;
- every metric the question names (sessions, engaged sessions, net revenue, buyers...): if the
  reference files define it, the SQL must compute exactly that definition. GA4's own built-in
  fields (for example the `session_engaged` parameter) do NOT replace our definitions;
- the 72-hour rule applies only to revenue figures or figures the analyst calls "final".

If it passes every check, reply with exactly: APPROVED
Otherwise reply with a short list of the problems and how to fix each one.""",
    tools=[
        SkillToolset(
            skills=[load_skill_from_dir(SKILL_DIR)],
            tool_filter=["list_skills", "load_skill", "load_skill_resource"],
        )
    ],
)
