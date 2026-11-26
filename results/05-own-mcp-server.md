# Lesson 5 results: our own MCP server

Run on 2026-11-26 by the user, with tests by Claude in a scratch copy first. Everything here is **verified** (terminal output, the catalog API, Langfuse traces) unless marked otherwise. **Status: done.**

## What we built

| File | What it does |
|---|---|
| `mcp_servers/okf/server.py` | An MCP server built with `MCPServer` (the `mcp` 2.x name for `FastMCP`). Three tools (`list_pages`, `get_page`, `search_pages`), a resource template `okf://pages/{name}` and a prompt `answer_from_pages`. It reads the Knowledge Studio pages **live** from Knowledge Catalog (the context set `ga4-merch-context`) through the Dataplex REST API, using Application Default Credentials. Optional cache: `OKF_CACHE_SECONDS` (default 0 = off). |
| `scripts/list_okf_tools.py` | A client: lists the tools and calls two of them, over stdio (starts the server itself) or HTTP (connects to port 8808). Prints each result's parts and the text inside. |
| `scripts/okf_resources_prompts.py` | Lists and reads the resource template and the prompt, in-process. |
| `agents/okf_guide/` | A small agent whose only toolset is our server (`StreamableHTTPConnectionParams`, `tool_filter` of the 3 tools). |

**Design change during the lesson:** the first version served 3 Markdown files copied from the kc-okf POC. We switched to reading the catalog live, because a copy drifts as soon as a reviewer approves a change in Studio (and `kcmd mcp` serves exactly such a copy). Now the catalog is the one source of truth.

## Step by step

| Step | Result |
|---|---|
| 1. List pages with `curl` | 8 entries in the context set: `agents`, `assets`, `assets/.../ga4_sample`, `assets/.../ga4_sample/events`, `documents`, 2 Studio topic pages and the hand-written playbook. All made in the kc-okf POC (Studio run 1 on Nov 22, playbook pushed with `kcmd push` on Nov 23); nothing in this lesson creates entries. Python ADC check printed `Credentials`. |
| 3. stdio | 3 tools with their docstrings as descriptions; `list_pages` returned 8 names with dates; `search_pages('72')` found the 72-hour rule in the `events` page (line 62) and the metrics page (line 19). Result parts: `['content', 'isError']`, no `structuredContent`. About 6–7 seconds per run. |
| 4. HTTP | Same output over `http://127.0.0.1:8808/mcp`. First attempt failed with `ConnectionError: ... All connection attempts failed`: the server in terminal A was not running. Starting it first fixed it. |
| 5. Duplicate copy | With `@mcp.tool()` on `list_pages`, `grep -c structuredContent` printed `1` (`['content', 'structuredContent', 'isError']`); with `structured_output=False` it is `0`. The duplicate comes from the server SDK's default. |
| 5b. Cache | 3 identical searches: cache off 2.00 / 1.69 / 1.59 s; `OKF_CACHE_SECONDS=60` 1.87 / 0.00 / 0.00 s. |
| 6. Resources and prompts | Template `okf://pages/{name}` (`~` stands for `/` inside a name), playbook text read through it, prompt `answer_from_pages` filled in. |
| 7. okf_guide | Answered question 1 from live pages and named the source page for every rule (details below). Question 2 was not run. |

## okf_guide vs ga4_guide on question 1

Question: "Which sensitivity tier covers geo.city, and why must daily revenue leave out the last 3 days?" One run each in a New Session (Langfuse).

| | okf_guide (our server, live pages) | ga4_guide (Lesson 4: skill + catalog + BigQuery) |
|---|---|---|
| Tool calls | 7: `list_pages`, 2 × `search_pages` (`geo.city`, `3 days`), 4 × `get_page` | 3 runs: (a) `remember_analyst`, `load_skill`, 2 × `load_skill_resource`, `execute_sql`; (b) the same; (c) `remember_analyst`, `load_skill`, 1 × `load_skill_resource` |
| Tool result sizes (characters, JSON) | list 955; searches 1,692 and 1,636; pages 1,664 (playbook), 8,216 (governance), 5,667 (`events`), 3,449 (metrics) | `load_skill` 2,249; references 1,142 and 1,227; `execute_sql` 110 |
| Model calls | 8 | 6, 6, 3 |
| First call's input | **475 tokens** (short instruction, 3 tools) | **9,658 tokens** (long instruction, 4 toolsets) |
| Last call's input | 7,121 tokens (4 pages read) | 5,669 uncached + 7,333 cached |
| Cost (Langfuse estimate) | **$0.059** | $0.096, $0.077, $0.049 |
| Answer | Correct (C3 restricted, roll up to region or country; 72-hour finality). Cited 3–4 pages per rule | Correct, same rules; no page sources; run (a) and (b) also checked the data's last date with SQL |

Findings:

1. **Both are right; they differ in where the rules come from.** ga4_guide reads a copy (the skill) and is as fresh as the day we wrote it. okf_guide reads the approved pages every time and names its sources.
2. **A small agent with a small menu is cheap to start.** okf_guide's first model call was 475 tokens against ga4_guide's 9,658. Its input then grows with each page it reads (whole pages, up to 8,216 characters).
3. **okf_guide read more than it needed.** It fetched all 4 pages after searching. A tighter instruction ("read only the pages the search points to") could cut that; not tested.
4. **Gemini caches repeated input by itself (implicit caching).** In ga4_guide's runs, calls 2 to 6 each had about 7,200 `input_cached_tokens`: the instruction and tool definitions, the same on every call. okf_guide had none: its repeated part is much shorter (**guess**: below the minimum size for caching). Cached tokens are billed at a lower rate (**docs**). This answers part of lesson 23's open question: gemini-3.5-flash on Vertex does implicit caching.

## What we learned (Q&A from the lesson)

- **Our server vs Google's catalog MCP server.** Google's server has 15 tools and some of them can probably fetch a page too (**guess**, not tested). Ours is for learning the server side, and adds a smaller menu, control over the output (no duplicate copy) and something we can deploy, register and guard later (lessons 10, 11).
- **Decorators decide what the server offers.** `@mcp.tool`, `@mcp.resource`, `@mcp.prompt` register a function; the name, docstring and type hints become what clients see. Functions without a decorator (`_get`, `_page_names`, `_read`) are helpers that clients never see.
- **Where the cache lives.** In the server's process memory, between the server and the catalog API. stdio starts a fresh process (and an empty cache) for each client; an HTTP server keeps its cache while it runs and shares it with every caller. For someone else's server, you can only cache on your side: an ADK callback or plugin, or session state (lesson 23).
- **`adk web agents`** starts one web server that lists every agent folder; it loads an agent when you first use it. The dropdown picks which one gets your message (our first question went to `ga4_guide` by mistake).
- **Why `jq` failed on Step 3's first version:** the script printed Python dicts (single quotes, `False`), not JSON.
- **Skill vs live pages.** A skill made from catalog pages is a copy and drifts. A sensible split (not built): the skill holds how to work and which page to read; the facts come live from the catalog.

## Not done

- Question 2 in okf_guide.
- Part B (Cloud Run): a plan only; it creates cloud resources, so we do it only after agreeing.
