"""Look at (or delete) what Memory Bank remembers (lesson 13). Free: no Gemini call for list.

  uv run python scripts/memories.py list              # every memory in ga4-guide's Memory Bank
  uv run python scripts/memories.py delete MEMORY     # one memory, by the name `list` printed

Memory Bank lives inside an Agent Runtime instance; we use the deployed ga4-guide's.
"""

import sys

import agentplatform

PROJECT = "kc-okf-poc-261122"
REGION = "us-central1"
ENGINE = f"projects/{PROJECT}/locations/{REGION}/reasoningEngines/7105399555822190592"

client = agentplatform.Client(project=PROJECT, location=REGION)


def show() -> None:
    n = 0
    for m in client.memory_banks.memories.list(name=ENGINE):
        n += 1
        scope = m.scope or {}
        print(f"- {m.fact}")
        print(f"    scope: app={scope.get('app_name')} user={scope.get('user_id')} | updated {m.update_time}")
        print(f"    name:  {m.name}")
    print(f"{n} memories")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "list":
        show()
    elif len(sys.argv) == 3 and sys.argv[1] == "delete":
        client.memory_banks.memories.delete(name=sys.argv[2])
        print("deleted", sys.argv[2])
    else:
        sys.exit(__doc__)
