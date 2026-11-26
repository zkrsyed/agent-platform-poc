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
