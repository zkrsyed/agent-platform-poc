"""Serve sql_reviewer over A2A on http://localhost:8001 (lesson 12).

    uv run uvicorn agents.sql_reviewer.a2a_app:app --port 8001

`to_a2a` builds the agent card from the agent (name, description, skills) and serves it at
/.well-known/agent-card.json, next to the A2A endpoint that receives messages.
"""

from google.adk.a2a.utils.agent_to_a2a import to_a2a

from .agent import root_agent

app = to_a2a(root_agent, host="localhost", port=8001)
