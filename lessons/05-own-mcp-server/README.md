# Lesson 5: Our own MCP server

**Goal:** build an MCP server that serves the catalog's pages about our table (the ones Knowledge Studio wrote) **by name, read live from Knowledge Catalog**, run it two ways (stdio and HTTP), look at its three kinds of offering (tools, resources, prompts), and let a small agent use it. About 60 minutes.

**Cost:** no Gemini for Steps 1 to 6; they only **read** the catalog (no change to anything; read calls cost nothing at our scale, **guess**). Step 7 is two Gemini questions (cents). **Part B (Cloud Run) creates cloud resources: we do not run it until we agree.**

## Why this lesson exists

In Lesson 4 the rules lived in a skill folder, so only an agent that **carries that folder** can use them. An **MCP server** offers the pages to **any** agent over a standard protocol, and a page changed in the catalog is what the next call returns, with no agent redeployed.

**Why read the catalog live, not copied files?** The pages already live in Knowledge Catalog (the context set `ga4-merch-context`, written by Studio and approved by a reviewer). `kcmd pull` could copy them to disk as OKF files, but a copy goes stale the moment someone approves a change in Studio (**drift**), and `kcmd mcp` serves exactly that copy. Our server reads the catalog on every call, so there is **one source of truth**. Compared with Google's catalog MCP server from Lesson 3, ours offers a **smaller menu**: fetch one page by name, instead of `lookup_context` returning about 36,700 characters (twice). It is also the piece that later gets deployed on its own (Cloud Run, Part B), listed in Agent Registry (lesson 10) and guarded by Agent Gateway (lesson 11).

Lesson 3 used Google's MCP servers as a **client**. Now you write the **server** side.

## The ideas

| Idea | One line | .NET comparison |
|---|---|---|
| **MCP server** | A program that publishes tools, resources and prompts in the MCP format | A Web API with an OpenAPI description |
| **Tool** | A function the **model** decides to call | A controller action |
| **Resource** | A piece of data the **application** attaches as context, addressed by a URI like `okf://pages/{name}` | A static file or blob with a URL |
| **Prompt** | A ready-made instruction the **user** picks | A saved query or template |
| **stdio transport** | The client starts the server as a **child process** and talks through its input and output | A console app piped to another |
| **Streamable HTTP transport** | The server runs on its own and listens on a URL, such as `http://127.0.0.1:8808/mcp` | A Web API |
| **`MCPServer`** | The class from the `mcp` package that builds a server. In `mcp` 2.x it replaces the old name `FastMCP` (**verified**: importing `mcp.server.fastmcp` fails and says so) | Minimal APIs |

**Who controls what:** tools are chosen by the model, resources by the application, prompts by the user. Our agent uses the tools; Step 6 shows the other two.

**stdio or HTTP?** stdio is simple and private to one machine: no port, no login, and the server stops with the client. HTTP is what you need when the server runs somewhere else and many agents share it, and then **you must secure it** (Part B).

## What you'll have at the end

```
mcp_servers/okf/
  server.py                 <- the server (reads the pages live from the catalog)
scripts/
  list_okf_tools.py         <- a client: stdio or HTTP
  okf_resources_prompts.py  <- resources and prompts
agents/okf_guide/
  __init__.py  agent.py     <- a small agent that uses only our server
```

---

## Step 1. See the pages in the catalog

Each page is an **entry** in the context set; its Markdown sits in the entry's `overview` aspect. First list them with the same REST call our server will make (read-only):

```bash
cd ~/apps/agent-platform-poc
curl -s -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://dataplex.googleapis.com/v1/projects/kc-okf-poc-261122/locations/us/entryGroups/ga4-merch-context/entries" \
  | grep '"name"'
```

**Look for:** 8 entry names ending in `agents`, `assets`, `assets/bigquery/kc-okf-poc-261122/ga4_sample`, `.../ga4_sample/events`, `documents`, and three under `documents/` (the metrics page, the governance page and the playbook). The part after `/entries/` is the **page name** our tools use.

Then check that Python can use your login (Application Default Credentials):

```bash
uv run python -c "import google.auth; print(google.auth.default()[0].__class__.__name__)"
```

**Look for:** `Credentials`. If it fails, run `gcloud auth application-default login`. (**verified**: on this machine both work, 2026-11-26.)

## Step 2. The server

Create **`mcp_servers/okf/server.py`**:

```python
"""Our own MCP server: serves the Knowledge Catalog pages about the GA4 table, read LIVE.

The pages are the `document` entries that Knowledge Studio wrote into the context set
`ga4-merch-context` (earlier kc-okf POC). We read them through the Dataplex REST API on every
call, so there is no copy on disk and nothing to drift.

  uv run python mcp_servers/okf/server.py         # stdio (a client starts it as a child process)
  uv run python mcp_servers/okf/server.py http    # Streamable HTTP on http://127.0.0.1:8808/mcp

Login: your Application Default Credentials (`gcloud auth application-default login`).
"""

import os
import sys
import time

import google.auth
from google.auth.transport.requests import AuthorizedSession
from mcp.server.mcpserver import MCPServer

CONTEXT_SET = os.environ.get(
    "OKF_CONTEXT_SET",
    "projects/kc-okf-poc-261122/locations/us/entryGroups/ga4-merch-context",
)
API = "https://dataplex.googleapis.com/v1/"
# How long to reuse an answer from the catalog. 0 (the default) means always ask the catalog.
CACHE_SECONDS = int(os.environ.get("OKF_CACHE_SECONDS", "0"))

mcp = MCPServer(
    "okf-pages",
    instructions=(
        "Documentation pages about the GA4 merchandise-store table, read live from Knowledge "
        "Catalog: business rules, metric definitions, privacy limits and a revenue playbook. "
        "Call list_pages first, then get_page for the one you need."
    ),
)

_creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
_http = AuthorizedSession(_creds)  # adds a fresh access token to every request


_cache: dict[str, tuple[float, dict]] = {}  # request -> (when we fetched it, the answer)


def _get(path: str, **params) -> dict:
    key = f"{path}?{sorted(params.items())}"
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]  # fresh enough: no API call
    r = _http.get(API + path, params=params, timeout=30)
    r.raise_for_status()
    _cache[key] = (time.monotonic(), r.json())
    return _cache[key][1]


def _page_names() -> dict[str, str]:
    """Page name -> last update date, straight from the catalog (one API call)."""
    entries = _get(f"{CONTEXT_SET}/entries", pageSize=100).get("entries", [])
    return {e["name"].split("/entries/", 1)[1]: e["updateTime"][:10] for e in entries}


def _read(name: str) -> str:
    """The Markdown text of one page: the entry's `overview` aspect."""
    entry = _get(f"{CONTEXT_SET}/entries/{name}", view="ALL")
    for key, aspect in entry.get("aspects", {}).items():
        if key.endswith(".global.overview"):  # key starts with a Google project number
            return aspect["data"].get("content", "")
    return ""


@mcp.tool(structured_output=False)
def list_pages() -> list[dict]:
    """List the pages in the catalog's context set: each page's name and last update date.
    Start with the page named 'agents': it is the index that says what the other pages cover."""
    return [{"name": n, "updated": d} for n, d in sorted(_page_names().items())]


@mcp.tool(structured_output=False)
def get_page(name: str) -> str:
    """Return the full Markdown text of one page, by the name list_pages gave
    (for example 'documents/playbook-final-daily-net-revenue')."""
    known = _page_names()
    if name not in known:  # only names the catalog listed are ever fetched
        raise ValueError(f"Unknown page {name!r}. Known pages: {', '.join(sorted(known))}")
    return _read(name)


@mcp.tool(structured_output=False)
def search_pages(query: str, max_results: int = 5) -> list[dict]:
    """Find lines that contain `query` (case-insensitive) across all pages.
    Returns page name, line number and the line. Use get_page to read the whole page."""
    hits = []
    for name in sorted(_page_names()):
        for i, line in enumerate(_read(name).splitlines(), start=1):
            if query.lower() in line.lower():
                hits.append({"page": name, "line": i, "text": line.strip()[:200]})
                if len(hits) >= max_results:
                    return hits
    return hits


@mcp.resource("okf://pages/{name}")
def page_resource(name: str) -> str:
    """One page as a resource. Use '~' for '/', e.g. okf://pages/documents~playbook-final-daily-net-revenue."""
    return get_page(name.replace("~", "/"))


@mcp.prompt()
def answer_from_pages(question: str) -> str:
    """A ready-made instruction: answer a question only from the catalog pages, citing them."""
    return (
        f"Answer this question using only the GA4 catalog pages: {question}\n"
        "Call list_pages, read the pages you need with get_page, and name the page "
        "each rule comes from. If the pages do not say, say so."
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "http":
        mcp.run("streamable-http", host="127.0.0.1", port=8808)
    else:
        mcp.run("stdio")
```

(The folder is still called `okf` because these are OKF-style pages: Markdown written for agents. Nothing here reads OKF files any more.)

Read it in this order:
- `MCPServer("okf-pages", instructions=...)` creates the server and gives it a name.
- `AuthorizedSession` is an HTTP client that adds your Google access token to every request. `_page_names()` makes **one** list call; `_read(name)` gets one entry with `view=ALL` and returns the text of its `overview` aspect. The aspect's key starts with a Google project number, so we match on the end, `.global.overview`.
- `_get` has a small **cache**, off by default (`OKF_CACHE_SECONDS=0`): every tool call asks the catalog, so you always get the approved version. That's slower (a `search_pages` call makes 9 API calls) but it can never drift. Step 5b turns the cache on and shows the trade-off.
- `@mcp.tool(...)` turns a plain Python function into a tool. The **function name** is the tool name, the **docstring** is the description the model reads, and the **type hints** become the input schema. Write good docstrings: they are the model's only manual.
- `structured_output=False` makes each tool return only the text copy of its result. Without it the SDK also sends a second, structured copy of the same data (Step 5 shows this).
- `@mcp.resource("okf://pages/{name}")` is a resource template: any `okf://pages/<page name>` is a resource.
- `@mcp.prompt()` offers a ready-made instruction.
- The last lines choose the transport: no argument means stdio, `http` means Streamable HTTP on port 8808.
- `get_page` first checks the name against the catalog's own list, raises an error for an unknown name and lists the known ones. So a name like `../../secret` is never sent to the API: only pages the catalog listed can be read.
- `OKF_CONTEXT_SET` (an environment variable) lets you point the same server at another context set.

## Step 3. Talk to it over stdio

Create **`scripts/list_okf_tools.py`**:

```python
"""Talk to our own OKF MCP server, over stdio or over HTTP. Free: no Gemini calls.

  uv run python scripts/list_okf_tools.py stdio    # starts the server as a child process
  uv run python scripts/list_okf_tools.py http     # connects to a server you started yourself on port 8808
"""

import asyncio
import sys
from pathlib import Path

from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams, StreamableHTTPConnectionParams
from mcp import StdioServerParameters

SERVER = Path(__file__).resolve().parents[1] / "mcp_servers" / "okf" / "server.py"


def make_toolset(mode: str) -> McpToolset:
    if mode == "stdio":
        params = StdioConnectionParams(
            server_params=StdioServerParameters(command=sys.executable, args=[str(SERVER)]),
        )
    else:
        params = StreamableHTTPConnectionParams(url="http://127.0.0.1:8808/mcp")
    return McpToolset(connection_params=params)


def show(result: dict) -> None:
    """Print what came back: the parts of the result, then the text inside each part."""
    print("result parts:", list(result))  # e.g. ['content', 'isError'] (Step 5 adds 'structuredContent')
    for part in result.get("content", []):
        print(part["text"])


async def main(mode: str) -> None:
    toolset = make_toolset(mode)
    try:
        tools = {t.name: t for t in await toolset.get_tools()}
        for name, tool in tools.items():
            print(f"{name:14} {(tool.description or '').splitlines()[0]}")
        print("\nlist_pages ->")
        show(await tools["list_pages"].run_async(args={}, tool_context=None))
        print("\nsearch_pages('72') ->")
        show(await tools["search_pages"].run_async(args={"query": "72", "max_results": 2}, tool_context=None))
    finally:
        await toolset.close()


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "stdio"))
```

Run it:

```bash
uv run python scripts/list_okf_tools.py stdio
```

**Look for:**
- three tools: `get_page`, `list_pages`, `search_pages`, with their descriptions
- `list_pages` returning the 8 pages, each with a name and the date it was last updated
- `search_pages('72')` returning lines that mention 72 (the 72-hour rule), from the `events` table page and the metrics page, with line numbers
- `result parts: ['content', 'isError']` for each result: the text copy and an error flag, **no** `structuredContent`
- the text inside each part, one JSON object per page or hit (`show()` prints just that text; the raw result is a Python dict, which is why piping it into `jq` fails)

You did not start the server. The client **launched it as a child process** (`StdioServerParameters`) and stopped it at the end. It takes a few seconds: each call goes to the catalog.

## Step 4. Run it over HTTP

You need two terminals. In **terminal A**, start the server:

```bash
cd ~/apps/agent-platform-poc && uv run python mcp_servers/okf/server.py http
```

**Look for:** `Uvicorn running on http://127.0.0.1:8808`. It now waits. Leave it running.

In **terminal B**:

```bash
cd ~/apps/agent-platform-poc && uv run python scripts/list_okf_tools.py http
```

**Look for:** the same tools and the same output as Step 3, and new request lines in terminal A. Only the connection changed: a URL instead of a child process. Keep terminal A running for Step 7.

## Step 5. See the duplicate copy (optional, 2 minutes)

In Lesson 3 the catalog's `lookup_context` result carried the same 36,700 characters twice. Now you can see where that comes from. In `server.py`, change `@mcp.tool(structured_output=False)` on `list_pages` to `@mcp.tool()` and run:

```bash
uv run python scripts/list_okf_tools.py stdio | grep -c structuredContent
```

**Look for:** `1`: `list_pages` now shows `result parts: ['content', 'structuredContent', 'isError']`, a second copy next to `content` (stdio starts a fresh server each time, so you don't restart anything). Put `structured_output=False` back. The duplicate comes from the **server's SDK**, so when you write the server you control it. For Google's hosted server we can't, which is why lesson 9 plans a plugin that strips one copy.

## Step 5b. Turn on the cache (optional, 2 minutes)

A **cache** keeps an answer for a while so the next identical request doesn't go to the catalog. Run the same search three times, first with the cache off, then with it kept for 60 seconds:

```bash
for c in 0 60; do echo "OKF_CACHE_SECONDS=$c"; OKF_CACHE_SECONDS=$c uv run python -c "
import time; from mcp_servers.okf import server as s
for i in range(3):
    t = time.time(); s.search_pages('72'); print(f'  search {i+1}: {time.time()-t:.2f}s')"; done
```

**Look for:** about 2 seconds for every search with `0`; with `60`, about 2 seconds for the first search and `0.00s` for the next two. (**verified**, 2026-11-26: 2.42 / 1.77 / 1.69 s, then 1.96 / 0.00 / 0.00 s.)

**The trade-off:** with the cache on, a page a reviewer approved in the last 60 seconds is not seen yet. That is drift again, but **bounded**: never older than 60 seconds, unlike a `kcmd pull` copy that stays stale until someone pulls again. Pick the number from how fresh the answer must be. Lesson 23 comes back to caching, for the **model** side (Gemini context caching), where the money is.

## Step 6. Resources and prompts

Create **`scripts/okf_resources_prompts.py`**:

```python
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
```

```bash
uv run python scripts/okf_resources_prompts.py
```

**Look for:** one resource template `okf://pages/{name}`, the playbook's text read through it (a URI can't hold `/` inside one part, so the resource writes `~` instead: `okf://pages/documents~playbook-final-daily-net-revenue`), one prompt `answer_from_pages`, and the prompt text with your question filled in. Our agent doesn't use these two, but a chat application could: a user picks the prompt, or attaches a page as context.

## Step 7. An agent that uses only our server

Create **`agents/okf_guide/__init__.py`** (the same tracing guard as `ga4_guide`, so its runs reach Langfuse):

```python
"""ga4_guide package. Importing it switches on tracing when the OTEL_* settings are present."""

from google.adk.telemetry.setup import maybe_set_otel_providers
from opentelemetry import trace

# `adk web` installs its own exporters at startup; `adk run` and plain scripts don't.
# So only act if nobody has installed a tracer provider yet.
if isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider):
    maybe_set_otel_providers()

from . import agent as agent  # noqa: E402
```

Create **`agents/okf_guide/agent.py`**:

```python
"""okf_guide: a small agent with ONE toolset, our own OKF MCP server.

It has no BigQuery, no catalog and no skill folder. Everything it knows about the table's rules
it fetches by page name from the server we built in lesson 5, which reads Knowledge Catalog
live (start the server first).
"""

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

okf = McpToolset(
    connection_params=StreamableHTTPConnectionParams(url="http://127.0.0.1:8808/mcp"),
    tool_filter=["list_pages", "get_page", "search_pages"],
)

root_agent = Agent(
    name="okf_guide",
    model="gemini-3.5-flash",
    description="Answers questions about the GA4 table's rules, using our catalog pages server.",
    instruction="""You answer questions about the rules for the GA4 merchandise-store table.
Use only the catalog pages server: call `list_pages`, then `get_page` for the page you need
(or `search_pages` for a quick look). For every rule you state, name the page it came from.
If the pages do not say, say so. Never invent rules.""",
    tools=[okf],
)
```

This agent has no BigQuery, no Google catalog tools and no skill. Everything it knows about the table's rules, it fetches by name from **our** server, which reads the catalog for it. With the server still running in terminal A, open a third terminal:

```bash
cd ~/apps/agent-platform-poc && ./scripts/adk.sh web agents
```

In the browser, pick **okf_guide** in the agent dropdown, open a **New Session**, and ask:

1. `Which sensitivity tier covers geo.city, and why must daily revenue leave out the last 3 days?`
2. `How do I compute final daily net revenue?`

**Look for** in the Events tab and in Langfuse:
- `get_page` calls with a page name, probably after `list_pages`
- an answer that says which page each rule came from
- the size of each tool result: a page is about 300 to 8,200 characters, far less than Lesson 3's catalog result (about 36,700 characters, sent twice). In my test run (**verified**, 2026-11-26) question 1 took 8 calls: `list_pages`, 3 `search_pages`, then `get_page` on 4 pages (1,663 to 8,171 characters each)
- `MCP send initialize` and `tools/list` rows at the start of each turn (the plumbing from Lesson 3)

Stop `adk web` with `Ctrl+C`, and the server in terminal A with `Ctrl+C`.

## Step 8. Commit

```bash
git status --short
git add mcp_servers/okf/server.py scripts/list_okf_tools.py scripts/okf_resources_prompts.py agents/okf_guide && git commit -m "Lesson 5: our own MCP server reading catalog pages live, and okf_guide"
```

---

## Part B (cloud, **not now**): the same server on Cloud Run

Everything above ran on your machine. For other agents (and Agent Registry) to use the server, it has to run on its own and be secured. The plan, to be done only after we agree on it (**docs**, not yet verified here):

- put the server in a container and deploy it to **Cloud Run** with no public access, so callers need the **Cloud Run Invoker** role;
- the server itself reads the catalog as a **service account** with a read-only catalog role (for example Dataplex Catalog Viewer), instead of your login;
- a caller proves who it is with a Google **ID token** for the service's URL, and our `McpToolset` sends it with `header_provider`, like Lesson 3's access token;
- the server code stays the same; only the transport (HTTP) and the hosting change.

Cloud Run creates a billable resource (small, probably within the free tier at our scale, **guess**), so I'll show you the exact commands and ask before anything is created.

## Check yourself

1. Which of the three things an MCP server offers does the **model** choose, which does the **application** choose, and which does the **user** choose?
2. Why did the client in Step 3 not need the server to be running?
3. What would break if an agent used the stdio version and you moved the server to another machine?
4. Where did the model's description of each tool come from?
5. Why does `get_page` check the name against the catalog's list before fetching it?
7. What would you see if a reviewer approved a changed page in Studio a minute ago? What would `kcmd mcp` show?
8. With `OKF_CACHE_SECONDS=300`, how old can a page be when the agent reads it? Why is that still better than a pulled copy?
6. In Step 5, where did the duplicate `structuredContent` come from, and why can we fix it here but not on Google's hosted server?

## Send me back

- The output of Step 3 (the tool list and `list_pages`) and whether `structuredContent` appeared
- What terminal A printed when you ran Step 4
- The two Step 7 answers, and the sizes of the `get_page` results in Langfuse
- Anything that didn't match this page

Next, lesson 6: **evaluate** the agent: `adk eval` on the 15 questions from the earlier POC, and a simulated user.
