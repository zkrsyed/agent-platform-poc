"""Look at, talk to, or delete our deployed agent on Agent Runtime (lesson 8).

  uv run python scripts/runtime.py info   RESOURCE          # name, identity, settings
  uv run python scripts/runtime.py principal RESOURCE        # the IAM member string for this agent (lesson 9)
  uv run python scripts/runtime.py ask    RESOURCE "question"
  uv run python scripts/runtime.py delete RESOURCE          # removes the deployed agent

RESOURCE is what `adk deploy` printed: projects/.../locations/us-central1/reasoningEngines/ID
(or just reasoningEngines/ID).
"""

import asyncio
import sys

import agentplatform  # the newer name of the Vertex AI SDK (vertexai.Client is deprecated)

PROJECT = "kc-okf-poc-261122"
REGION = "us-central1"

client = agentplatform.Client(project=PROJECT, location=REGION)


def info(name: str) -> None:
    agent = client.runtimes.get(name=name)
    r = agent.api_resource
    spec = r.spec
    print("name:              ", r.name)
    print("display name:      ", r.display_name)
    print("created / updated: ", r.create_time, "/", r.update_time)
    print("identity type:     ", getattr(spec, "identity_type", None))
    print("runs as:           ", getattr(spec, "effective_identity", None))


def principal(name: str) -> None:
    """Print the agent's identity in the form IAM commands want: principal://..."""
    agent = client.runtimes.get(name=name)
    print("principal://" + agent.api_resource.spec.effective_identity)


async def ask(name: str, question: str) -> None:
    agent = client.runtimes.get(name=name)
    async for event in agent.async_stream_query(user_id="lesson8", message=question):
        author = event.get("author", "?")
        for part in (event.get("content") or {}).get("parts", []):
            if "function_call" in part:
                print(f"[{author}] CALL {part['function_call']['name']}")
            elif "function_response" in part:
                print(f"[{author}] RESULT {str(part['function_response'].get('response'))[:300]}")
            elif part.get("text") and not part.get("thought"):
                print(f"[{author}] {part['text']}")


def delete(name: str) -> None:
    client.runtimes.delete(name=name, force=True)  # force: also delete its sessions
    print("deleted", name)


if __name__ == "__main__":
    command, name = sys.argv[1], sys.argv[2]
    if command == "info":
        info(name)
    elif command == "principal":
        principal(name)
    elif command == "ask":
        asyncio.run(ask(name, sys.argv[3]))
    elif command == "delete":
        delete(name)
    else:
        sys.exit(__doc__)
