# Lesson 5: Our own MCP server

**Goal:** build an MCP server that serves the OKF pages (the rules about our table) **by name**, run it two ways (stdio and HTTP), look at its three kinds of offering (tools, resources, prompts), and let a small agent use it. About 60 minutes.

**Cost:** nothing for Steps 1 to 6 (no Gemini, no GCP). Step 7 is two Gemini questions (cents). **Part B (Cloud Run) creates cloud resources: we do not run it until we agree.**

## Why this lesson exists

In Lesson 4 the rules lived in a skill folder, so only an agent that **carries that folder** can use them. An **MCP server** offers the same pages to **any** agent over a standard protocol, and you can change a page without redeploying any agent. It is also the piece that later gets deployed on its own (Cloud Run, Part B), listed in Agent Registry (lesson 10) and guarded by Agent Gateway (lesson 11).

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
  server.py                 <- the server
  pages/                    <- three OKF pages (copied from the kc-okf POC)
scripts/
  list_okf_tools.py         <- a client: stdio or HTTP
  okf_resources_prompts.py  <- resources and prompts
agents/okf_guide/
  __init__.py  agent.py     <- a small agent that uses only our server
```

---

## Step 1. Copy the pages

The pages come from the earlier kc-okf POC (that repo is the source of truth). We copy three of them:

```bash
cd ~/apps/agent-platform-poc
mkdir -p mcp_servers/okf/pages
cp ~/apps/kc-okf/results/04-okf/workspace/bundle/documents/*.md mcp_servers/okf/pages/
ls -l mcp_servers/okf/pages
```

**Look for:** three files: `computing-standard-ecommerce-metrics.md` (about 3.8 KB), `data-governance-and-quality-boundaries.md` (about 8.5 KB) and `playbook-final-daily-net-revenue.md` (about 1.9 KB).

## Step 2. The server

Create **`mcp_servers/okf/server.py`**:

```python
"""Our own MCP server: it serves the OKF documentation pages about the GA4 table.

Run it two ways (same code, different transport):
  uv run python mcp_servers/okf/server.py                      # stdio: a client starts it as a child process
  uv run python mcp_servers/okf/server.py http                 # Streamable HTTP on http://127.0.0.1:8808/mcp
"""

import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

PAGES_DIR = Path(__file__).parent / "pages"

mcp = MCPServer(
    "okf-pages",
    instructions=(
        "Documentation pages about the GA4 merchandise-store table: metric definitions, "
        "data governance and quality rules, and the final daily net revenue playbook. "
        "Call list_pages first, then get_page for the one you need."
    ),
)


def _load_pages() -> dict[str, str]:
    """Read every page into memory: {page name: full text}. The name is the file name without .md."""
    return {p.stem: p.read_text(encoding="utf-8") for p in sorted(PAGES_DIR.glob("*.md"))}


PAGES = _load_pages()


def _title(text: str) -> str:
    """The first '# ' heading is the page title."""
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


@mcp.tool(structured_output=False)
def list_pages() -> list[dict]:
    """List the available pages: their name, title and size. Call this first."""
    return [{"name": n, "title": _title(t), "characters": len(t)} for n, t in PAGES.items()]


@mcp.tool(structured_output=False)
def get_page(name: str) -> str:
    """Return the full text of one page. `name` is one of the names from list_pages."""
    if name not in PAGES:
        raise ValueError(f"Unknown page {name!r}. Known pages: {', '.join(PAGES)}")
    return PAGES[name]


@mcp.tool(structured_output=False)
def search_pages(query: str, max_results: int = 5) -> list[dict]:
    """Find lines that contain the query text (case-insensitive). Returns page name, line number and the line."""
    q = query.lower()
    hits = []
    for name, text in PAGES.items():
        for number, line in enumerate(text.splitlines(), start=1):
            if q in line.lower():
                hits.append({"page": name, "line": number, "text": line.strip()[:200]})
    return hits[:max_results]


@mcp.resource("okf://pages/{name}")
def page_resource(name: str) -> str:
    """The same pages, offered as resources that a client application can attach as context."""
    return get_page(name)


@mcp.prompt()
def answer_from_pages(question: str) -> str:
    """A ready-made instruction a user can pick: answer a question only from the OKF pages."""
    return (
        f"Answer this question using only the OKF pages. Call list_pages, then get_page for the "
        f"pages you need, and name the page you used for each rule.\n\nQuestion: {question}"
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "http":
        mcp.run("streamable-http", host="127.0.0.1", port=8808)
    else:
        mcp.run("stdio")
```

Read it in this order:
- `MCPServer("okf-pages", instructions=...)` creates the server and gives it a name.
- `@mcp.tool(...)` turns a plain Python function into a tool. The **function name** is the tool name, the **docstring** is the description the model reads, and the **type hints** become the input schema. Write good docstrings: they are the model's only manual.
- `structured_output=False` makes each tool return only the text copy of its result. Without it the SDK also sends a second, structured copy of the same data (Step 5 shows this).
- `@mcp.resource("okf://pages/{name}")` is a resource template: any `okf://pages/<page name>` is a resource.
- `@mcp.prompt()` offers a ready-made instruction.
- The last lines choose the transport: no argument means stdio, `http` means Streamable HTTP on port 8808.
- `get_page` raises an error for an unknown name and lists the known ones. A page name is only ever a dictionary key, never a file path, so a name like `../../secret` can't read other files.

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


async def main(mode: str) -> None:
    toolset = make_toolset(mode)
    try:
        tools = {t.name: t for t in await toolset.get_tools()}
        for name, tool in tools.items():
            print(f"{name:14} {(tool.description or '')[:70]!r}")
        print("\nlist_pages ->")
        print(await tools["list_pages"].run_async(args={}, tool_context=None))
        print("\nsearch_pages('72') ->")
        print(await tools["search_pages"].run_async(args={"query": "72", "max_results": 2}, tool_context=None))
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
- `list_pages` returning the three pages, each with a name, title and size
- `search_pages('72')` returning lines that mention 72 (the 72-hour rule), with page name and line number
- only `content` in each result, **no** `structuredContent`

You did not start the server. The client **launched it as a child process** (`StdioServerParameters`) and stopped it at the end.

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

**Look for:** a number above 0: the result now has a `structuredContent` copy next to `content` (stdio starts a fresh server each time, so you don't restart anything). Put `structured_output=False` back. The duplicate comes from the **server's SDK**, so when you write the server you control it. For Google's hosted server we can't, which is why lesson 9 plans a plugin that strips one copy.

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
    parts = await mcp.read_resource("okf://pages/playbook-final-daily-net-revenue")
    print("resource text starts:", parts[0].content[:60].replace("\n", " "), "...")
    print("prompts:", [p.name for p in await mcp.list_prompts()])
    prompt = await mcp.get_prompt("answer_from_pages", {"question": "Why drop the last 3 days?"})
    print("prompt text:", prompt.messages[0].content.text[:120].replace("\n", " "), "...")


asyncio.run(main())
```

```bash
uv run python scripts/okf_resources_prompts.py
```

**Look for:** one resource template `okf://pages/{name}`, the playbook's text read through it, one prompt `answer_from_pages`, and the prompt text with your question filled in. Our agent doesn't use these two, but a chat application could: a user picks the prompt, or attaches a page as context.

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
it fetches by page name from the server we built in lesson 5 (start the server first).
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
    description="Answers questions about the GA4 table's rules, using the OKF pages server.",
    instruction="""You answer questions about the rules for the GA4 merchandise-store table.
Use only the OKF pages server: call `list_pages`, then `get_page` for the page you need
(or `search_pages` for a quick look). For every rule you state, name the page it came from.
If the pages do not say, say so. Never invent rules.""",
    tools=[okf],
)
```

This agent has no BigQuery, no catalog and no skill. Everything it knows about the table's rules, it fetches by name from the server. With the server still running in terminal A, open a third terminal:

```bash
cd ~/apps/agent-platform-poc && ./scripts/adk.sh web agents
```

In the browser, pick **okf_guide** in the agent dropdown, open a **New Session**, and ask:

1. `Which sensitivity tier covers geo.city, and why must daily revenue leave out the last 3 days?`
2. `How do I compute final daily net revenue?`

**Look for** in the Events tab and in Langfuse:
- `get_page` calls with a page name, probably after `list_pages`
- an answer that says which page each rule came from
- the size of each tool result: a page is 1,900 to 8,544 characters, far less than Lesson 3's catalog result (about 36,700 characters, sent twice)
- `MCP send initialize` and `tools/list` rows at the start of each turn (the plumbing from Lesson 3)
- the service name in Langfuse is still `ga4_guide`, because `OTEL_SERVICE_NAME` is set once in `.env`; the span names should say `okf_guide` (**guess**, as for `ga4_guide` in Lesson 2)

Stop `adk web` with `Ctrl+C`, and the server in terminal A with `Ctrl+C`.

## Step 8. Commit

```bash
git status --short
git add mcp_servers scripts/list_okf_tools.py scripts/okf_resources_prompts.py agents/okf_guide && git commit -m "Lesson 5: our own OKF MCP server and okf_guide agent"
```

---

## Part B (cloud, **not now**): the same server on Cloud Run

Everything above ran on your machine. For other agents (and Agent Registry) to use the server, it has to run on its own and be secured. The plan, to be done only after we agree on it (**docs**, not yet verified here):

- put the server in a container and deploy it to **Cloud Run** with no public access, so callers need the **Cloud Run Invoker** role;
- a caller proves who it is with a Google **ID token** for the service's URL, and our `McpToolset` sends it with `header_provider`, like Lesson 3's access token;
- the server code stays the same; only the transport (HTTP) and the hosting change.

Cloud Run creates a billable resource (small, probably within the free tier at our scale, **guess**), so I'll show you the exact commands and ask before anything is created.

## Check yourself

1. Which of the three things an MCP server offers does the **model** choose, which does the **application** choose, and which does the **user** choose?
2. Why did the client in Step 3 not need the server to be running?
3. What would break if an agent used the stdio version and you moved the server to another machine?
4. Where did the model's description of each tool come from?
5. Why does `get_page` take a page **name** and look it up in a dictionary, instead of opening a file by that name?
6. In Step 5, where did the duplicate `structuredContent` come from, and why can we fix it here but not on Google's hosted server?

## Send me back

- The output of Step 3 (the tool list and `list_pages`) and whether `structuredContent` appeared
- What terminal A printed when you ran Step 4
- The two Step 7 answers, and the sizes of the `get_page` results in Langfuse
- Anything that didn't match this page

Next, lesson 6: **evaluate** the agent: `adk eval` on the 15 questions from the earlier POC, and a simulated user.
