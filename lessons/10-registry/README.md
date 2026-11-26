# Lesson 10: Agent Registry: agents, MCP servers and skills ☁

**Goal:** see the project's agents, MCP servers and skills in one catalog, **Agent Registry**; register our own MCP server and our skill there; and build an agent that **finds** its skill and its catalog tools in the registry instead of having them hard-coded. About 75 minutes.

**Cost (docs):** "Registry storage" and "Registry discovery, search, and Agent Registry API operations" are "Included at no charge ($0.00)". The only charge is skill vulnerability **scanning** ($8.00 per 1 million tokens from 1 January 2027, free until then), and it runs only if you turn it on. A couple of Gemini questions in Step 12 (cents).

**This lesson changes the project:** Step 1 enables an API; Steps 7 and 9 create registry entries. You run them; tell me first if you want to go through anything.

## Why this lesson exists

So far every connection is hard-coded: `ga4_guide` has the catalog URL in its code and the skill copied into its folder (Lesson 8 had to copy it into the build). With three agents that's fine. With thirty, across teams, nobody knows what exists, who owns it, or which version is current.

**Agent Registry** is the phone book: agents, MCP servers and skills, each with a description and connection details. Agents and people **search** it, and code asks it "how do I reach X?" instead of carrying the address. It's also what lesson 11's Gateway uses to know which servers exist, and what A2A (lesson 12) uses to find other agents.

## The ideas

| Idea | One line | .NET comparison |
|---|---|---|
| **Agent Registry** | A catalog of agents, MCP servers, endpoints and skills, with search (`agentregistry.googleapis.com`) | A service registry, or NuGet's search |
| **Automatic registration** | Agent Runtime agents and Google's own MCP servers appear by themselves (**docs**) | Packages a build server publishes for you |
| **Service** | What *you* create to register something by hand: an agent, an MCP server or an endpoint. The registry then shows it as a read-only Agent, McpServer or Endpoint | Publishing a package |
| **Tool spec** | The list of an MCP server's tools (name, description, input schema) stored with its entry, up to 150 KB | The API docs on a package page |
| **Skill (in the registry)** | A ZIP with `SKILL.md` at its root (max 1 MB), with revisions and a state: Draft, Active, Disabled... Only Active skills can be downloaded | A package version |
| **Discovery** | Code looks something up by name and gets its address and auth from the registry | DI with a service locator |

**Locations:** "All resources in Agent Registry are supported in the `global` location", and Google's MCP servers are created only in `global` (**docs**). We use `global` throughout, but check `us-central1` too for our agent (Step 2).

---

## Part A: turn it on and look around

### Step 1. Enable the API ☁

```bash
cd ~/apps/agent-platform-poc
gcloud services enable agentregistry.googleapis.com --project kc-okf-poc-261122
```

(**verified** before the lesson: without it, the registry answers "Agent Registry API has not been used in project ... or it is disabled".) Then save the scripts from the end of this page: `scripts/registry.py`, `scripts/mcp_toolspec.py`, `scripts/skill_registry.py`.

### Step 2. Our agent, registered by itself

```bash
uv run python scripts/registry.py agents global
uv run python scripts/registry.py agents us-central1
gcloud agent-registry agents list --project kc-okf-poc-261122 --location global
```

**Look for:** `ga4-guide`. The docs say Agent Runtime agents are registered automatically, but not in which location; that's why we look in both (**to check**). It may take a few minutes after enabling the API.

### Step 3. What the registry knows about it

```bash
uv run python scripts/registry.py show NAME
```

Use the full `name` that Step 2 printed. **Look for:** whether there's an **agent card** (an A2A description of the agent's skills and protocol, which lesson 12 needs) or only basic details. That's an open question in our lesson plan: a blog said auto-registered agents get a `CUSTOM` entry without a card (**guess**).

### Step 4. Google's MCP servers, registered by themselves

```bash
uv run python scripts/registry.py mcp global
```

**Look for:** Google's MCP servers for APIs this project uses, probably including the Knowledge Catalog (Dataplex) and BigQuery ones. The docs say Google's remote MCP servers "are automatically registered" when you enable an API that has one (**docs**).

### Step 5. Connect to an MCP server through the registry

Pick the Knowledge Catalog's entry from Step 4 and:

```bash
uv run python scripts/registry.py tools NAME
```

`get_mcp_toolset(NAME)` asks the registry for the server's **address and auth**, then connects. **Look for:** the same tools as Lesson 3 (`search_entries`, `lookup_context`, ...), but our code never wrote `https://dataplex.googleapis.com/mcp`. (Not yet verified: ADK resolves auth "from the server's IAM bindings"; if this step fails on auth, send me the error.)

Also open **Agents → Govern → Agent Registry** in the console and find the same entries.

---

## Part B: register our own MCP server

### Step 6. Its tool spec (local, free)

```bash
uv run python scripts/mcp_toolspec.py
```

It starts our Lesson 5 server over stdio, asks for its tools, and writes `build/okf_toolspec.json`. **Look for:** `3 tools (list_pages, get_page, search_pages), 1485 bytes` (**verified**).

### Step 7. Register it ☁

```bash
gcloud agent-registry services create okf-pages --project kc-okf-poc-261122 --location global \
  --display-name "OKF pages (lesson 5)" \
  --description "Knowledge Studio pages about the GA4 table, read live from Knowledge Catalog: list_pages, get_page, search_pages." \
  --mcp-server-spec-type tool-spec --mcp-server-spec-content build/okf_toolspec.json \
  --interfaces url=http://127.0.0.1:8808/mcp,protocolBinding=jsonrpc
```

**An honest limit:** our server runs only on your machine, so its address is `127.0.0.1`. The registry will list it with its tools and description, so people can **find** it, but nobody else can **reach** it until it runs on Cloud Run (Lesson 5's Part B). That's a real situation too: the entry documents the server; the address changes when it moves. (Syntax from `gcloud agent-registry services create --help` and the docs; the run itself is **not yet verified**.)

### Step 8. Find it

```bash
uv run python scripts/registry.py mcp global
```

**Look for:** `OKF pages (lesson 5)` next to Google's servers. You registered a **service**; the registry shows it as an **MCP server** (**docs**).

---

## Part C: the skill in the registry

### Step 9. Upload it ☁

Our `gcloud` has no `agent-registry skills` commands (**verified**: "Invalid choice: 'skills'"), so the script calls the REST API:

```bash
uv run python scripts/skill_registry.py upload
```

It zips `skills/ga4-context` (`SKILL.md` and the two reference files at the ZIP's root, 2,649 bytes, **verified**) and creates a skill with ID `ga4-context`; the registry adds a `private-` prefix (**docs**). The answer is a long-running **operation**.

### Step 10. Make it Active

New skills start as Draft or Disabled, and only Active skills can be downloaded (**docs**).

```bash
uv run python scripts/skill_registry.py list
uv run python scripts/skill_registry.py show private-ga4-context
```

Copy the revision's full `name` (`projects/.../skills/private-ga4-context/revisions/...`), then:

```bash
uv run python scripts/skill_registry.py activate private-ga4-context REVISION_NAME
```

(The field names in `upload` and `activate` come from Google's REST docs and are **not yet verified**; if one fails, the script prints Google's error and we fix it together.)

### Step 11. Search for it

```bash
uv run python scripts/skill_registry.py search "rules for querying GA4 revenue"
```

**Look for:** our skill in the results. This is the same call an ADK agent makes through `search_skills`.

### Step 12. An agent that finds its skill in the registry

Create **`agents/ga4_registry/__init__.py`** (the tracing guard, as before):

```python
"""ga4_registry package. Importing it switches on tracing when the OTEL_* settings are present."""

from google.adk.telemetry.setup import maybe_set_otel_providers
from opentelemetry import trace

# `adk web` installs its own exporters at startup; `adk run` and plain scripts don't.
# So only act if nobody has installed a tracer provider yet.
if isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider):
    maybe_set_otel_providers()

from . import agent as agent  # noqa: E402
```

Create **`agents/ga4_registry/agent.py`**:

```python
"""ga4_registry (lesson 10): ga4_guide's skill and catalog, found in Agent Registry instead of hard-coded.

- The skill comes from the registry: SkillToolset(registry=GCPSkillRegistry(...)) gives the agent a
  `search_skills` tool, and `load_skill` downloads a registry skill by name.
- The catalog MCP server comes from the registry too: we look it up by name, and the registry
  supplies its URL (no "https://dataplex.googleapis.com/mcp" in this file).
"""

import os

from google.adk.agents import Agent
from google.adk.integrations.agent_registry import AgentRegistry
from google.adk.integrations.skill_registry import GCPSkillRegistry
from google.adk.models import Gemini
from google.adk.tools.skill_toolset import SkillToolset

PROJECT = "kc-okf-poc-261122"
MODEL = Gemini(model="gemini-3.5-flash", client_kwargs={"enterprise": True, "location": "global"})

# The registry entry for Google's Knowledge Catalog MCP server. Find the name with
#   uv run python scripts/registry.py mcp
CATALOG_MCP_NAME = os.environ.get("CATALOG_MCP_NAME", "")

skills = SkillToolset(
    registry=GCPSkillRegistry(project_id=PROJECT, location="global"),
    tool_filter=["search_skills", "load_skill", "load_skill_resource"],
)

tools = [skills]
if CATALOG_MCP_NAME:
    tools.append(AgentRegistry(project_id=PROJECT, location="global").get_mcp_toolset(CATALOG_MCP_NAME))

root_agent = Agent(
    name="ga4_registry",
    model=MODEL,
    description="Explains the rules for the GA4 table, using a skill found in Agent Registry.",
    instruction="""You explain the data team's rules for the BigQuery table
`kc-okf-poc-261122.ga4_sample.events`. You have no skill folder of your own: first call
`search_skills` to find the right skill in the registry, then `load_skill` with the name it returns,
and answer from it. Use the catalog tools only if the skill doesn't cover the question.
Say which skill (and catalog entry) each answer came from. Never invent rules.""",
    tools=tools,
)
```

What's different from `ga4_guide`:
- `SkillToolset(registry=GCPSkillRegistry(...))` with **no** `skills=[...]`: the agent has no skill folder. ADK adds a `search_skills` tool, and `load_skill` downloads a registry skill by name (**verified** in ADK's code).
- The catalog tools come from `AgentRegistry(...).get_mcp_toolset(CATALOG_MCP_NAME)`, where `CATALOG_MCP_NAME` is the Knowledge Catalog entry's full name from Step 4. It's read from the agent's own `.env` (`adk web` loads an agent folder's `.env` before importing it, as its log shows: "Loaded .env file for ..."). Without it, the agent runs with the skill only.
- It imports and builds locally (**verified**); the run is **not yet verified**.

Give the agent its own `.env` (a copy of `ga4_guide`'s, for the Google settings and tracing), add one line, and start the dev UI:

```bash
cp agents/ga4_guide/.env agents/ga4_registry/.env
echo 'CATALOG_MCP_NAME=projects/.../locations/global/mcpServers/...' >> agents/ga4_registry/.env
./scripts/adk.sh web agents
```

Replace the `CATALOG_MCP_NAME` value with the name from Step 4. Pick **ga4_registry**, New Session, and ask: `Why must daily revenue leave out the last 3 days?`

**Look for:** `search_skills`, then `load_skill` with the registry's skill name (probably `private-ga4-context`), then an answer that cites it.

### Step 13. Commit

```bash
git status --short
git add scripts/registry.py scripts/mcp_toolspec.py scripts/skill_registry.py agents/ga4_registry/__init__.py agents/ga4_registry/agent.py && git commit -m "Lesson 10: Agent Registry: discovery, our MCP server and skill registered, ga4_registry agent"
```

(`agents/ga4_registry/.env` is ignored by git, like the others.)

---

## The scripts

**`scripts/registry.py`**:

```python
"""Look things up in Agent Registry with ADK's client (lesson 10). Reads only.

  uv run python scripts/registry.py agents [LOCATION]        # agents (ours is auto-registered)
  uv run python scripts/registry.py mcp    [LOCATION]        # MCP servers (Google's + ours)
  uv run python scripts/registry.py show   NAME              # everything the registry knows about one entry
  uv run python scripts/registry.py tools  NAME              # connect to a registered MCP server and list its tools

LOCATION defaults to "global". NAME is the full resource name that `agents` or `mcp` printed.
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


def show(name: str) -> None:
    location = name.split("/locations/")[1].split("/")[0]
    reg = registry(location)
    info = reg.get_agent_info(name) if "/agents/" in name else reg.get_mcp_server(name)
    print(json.dumps(info, indent=2)[:4000])


async def tools(name: str) -> None:
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
```

**`scripts/mcp_toolspec.py`**:

```python
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
```

**`scripts/skill_registry.py`**:

```python
"""Put our skill in Agent Registry and find it again (lesson 10).

  uv run python scripts/skill_registry.py upload            # zip skills/ga4-context and create the skill
  uv run python scripts/skill_registry.py list              # the skills in the registry
  uv run python scripts/skill_registry.py show SKILL_ID     # one skill, with its revisions and state
  uv run python scripts/skill_registry.py activate SKILL_ID REVISION_NAME
  uv run python scripts/skill_registry.py search "QUERY"    # search the way an ADK agent does

Our gcloud has no `agent-registry skills` commands, so this calls the REST API (docs:
docs.cloud.google.com/agent-registry/register-skills and manage-skills). The registry stores the skill
as a ZIP with SKILL.md at its root (max 1 MB) and gives it an ID starting with "private-".
"""

import asyncio
import base64
import io
import json
import sys
import zipfile
from pathlib import Path

import google.auth
from google.auth.transport.requests import AuthorizedSession

PROJECT = "kc-okf-poc-261122"
LOCATION = "global"
ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "ga4-context"
API = f"https://agentregistry.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}"

creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
http = AuthorizedSession(creds)


def call(method: str, url: str, **kwargs) -> dict:
    r = http.request(method, url, headers={"x-goog-user-project": PROJECT}, timeout=60, **kwargs)
    if not r.ok:
        sys.exit(f"{r.status_code} {r.text[:800]}")
    return r.json() if r.text else {}


def zip_skill() -> bytes:
    """SKILL.md and references/ at the root of the ZIP, as the registry expects."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(SKILL_DIR.rglob("*")):
            if path.is_file():
                z.write(path, path.relative_to(SKILL_DIR).as_posix())
    return buffer.getvalue()


def upload() -> None:
    archive = zip_skill()
    print(f"zipped {SKILL_DIR.relative_to(ROOT)}: {len(archive)} bytes")
    body = {
        "displayName": "GA4 context",
        "description": "Rules and definitions for querying the GA4 merchandise-store table correctly.",
        "initialRevision": {"archiveUploadSource": {"archiveContent": base64.b64encode(archive).decode()}},
    }
    print(json.dumps(call("POST", f"{API}/skills", params={"skillId": "ga4-context"}, json=body), indent=2))


def show_list() -> None:
    for skill in call("GET", f"{API}/skills").get("skills", []):
        print(f"- {skill['name']}  state={skill.get('state')}  default={skill.get('defaultRevision')}")


def show(skill_id: str) -> None:
    print(json.dumps(call("GET", f"{API}/skills/{skill_id}"), indent=2))
    print(json.dumps(call("GET", f"{API}/skills/{skill_id}/revisions"), indent=2))


def activate(skill_id: str, revision: str) -> None:
    """Make the revision the default and the skill Active, so agents can download it."""
    body = {"defaultRevision": revision, "targetState": "TARGET_STATE_ACTIVE"}
    print(json.dumps(call("PATCH", f"{API}/skills/{skill_id}",
                          params={"updateMask": "defaultRevision,targetState"}, json=body), indent=2))


async def search(query: str) -> None:
    from google.adk.integrations.skill_registry import GCPSkillRegistry
    registry = GCPSkillRegistry(project_id=PROJECT, location=LOCATION)
    for found in await registry.search_skills(query=query):
        print(f"- {found.name}: {found.description[:100]}")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "upload":
        upload()
    elif command == "list":
        show_list()
    elif command == "show":
        show(sys.argv[2])
    elif command == "activate":
        activate(sys.argv[2], sys.argv[3])
    elif command == "search":
        asyncio.run(search(sys.argv[2]))
    else:
        sys.exit(__doc__)
```

## What's next with the registry

- The **deployed** agent would need `roles/agentregistry.viewer` to look things up in the registry (**docs**: viewer can "view and search all registry resources"). Lesson 12 uses that, when the orchestrator finds the policy agent in the registry and calls it over A2A.
- Registering our MCP server with a **real** address needs it on Cloud Run (Lesson 5, Part B).

## Check yourself

1. Which entries appeared without you registering anything, and why?
2. What's the difference between a **service** you create and the **MCP server** the registry shows?
3. Why can people find our `okf-pages` server in the registry but not use it yet?
4. Why must a registry skill be **Active** before an agent can load it?
5. What did `ga4_registry` *not* have in its code that `ga4_guide` has?

## Send me back

- Where `ga4-guide` showed up (global or us-central1) and what `show` printed (agent card or not)
- The MCP servers in Step 4, and whether Step 5 connected
- Whether `services create` (Step 7) and the skill `upload` / `activate` (Steps 9 and 10) worked, with any error
- What `ga4_registry` did in Step 12

Next, lesson 11: **Agent Gateway and policies**: block a tool on the network, whatever the agent's code says.
