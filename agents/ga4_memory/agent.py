"""ga4_memory (lesson 13): ga4_guide plus long-term memory (Agent Platform Memory Bank).

Two kinds of "remembering" in this repo:

  user: state (lesson 2)  keys WE choose and write in code (user:analyst_name). Exact, cheap.
  Memory Bank (lesson 13) Google's model READS the conversation and keeps short facts
                          ("Priya prefers weekly figures"). Later sessions SEARCH them by meaning.

Two changes from ga4_guide, everything else is reused:
  1. preload_memory: before each Gemini call, ADK searches Memory Bank with the analyst's message
     and adds what it finds to the prompt. (load_memory would let the model decide when to search.)
  2. after_agent_callback: after each answer, send the session to Memory Bank, which extracts facts.

Memory Bank is a feature of an Agent Runtime instance. We reuse the deployed ga4-guide's:
  ./scripts/adk.sh web --memory_service_uri=agentengine://7105399555822190592 agents
Memories are kept per app name (ga4_memory) and user id.
"""

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.tools import preload_memory

from ga4_guide import agent as guide  # the lesson 4-9 agent: model, tools, instruction
from ga4_guide.guardrails import GuardrailsPlugin


async def save_to_memory(callback_context: CallbackContext) -> None:
    """After each answer: hand the conversation to Memory Bank (it decides what is worth keeping)."""
    await callback_context.add_session_to_memory()


root_agent = Agent(
    name="ga4_memory",
    model=guide.MODEL,
    description=guide.root_agent.description,
    instruction=guide.root_agent.instruction
    + """

Long-term memory: facts from earlier conversations with this analyst may appear below as past
conversations. Follow their stated preferences (for example weekly figures, or a revenue
definition) unless they ask otherwise, and say when a preference changed your answer.""",
    tools=[guide.remember_analyst, guide.catalog, guide.bigquery, guide.skills, preload_memory],
    after_agent_callback=save_to_memory,
)

app = App(name="ga4_memory", root_agent=root_agent, plugins=[GuardrailsPlugin()])
