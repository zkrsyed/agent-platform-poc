# Glossary

Every term this POC touches, explained in one line with a .NET or SQL Server comparison where one helps. "Lesson" is where you first use the term. Each entry is **docs** (from Google's docs or a spec) until a lesson verifies it.

## Agent basics

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **Agent** | A program that loops: the LLM reads the context, picks a tool, sees the result, and repeats until it can answer | A controller whose logic is decided at runtime by a model | 0 |
| **Context engineering** | Choosing what the model sees: instructions, tool results, docs, memory | Building the right query plan inputs | 0 |
| **Grounding** | Making answers rely on real sources (the catalog, the data) rather than the model's memory | Joining to the source of truth instead of guessing | 3 |
| **Prompt injection** | Text in data or tool output that tries to give the agent instructions | SQL injection, but in natural language | 11 |

## ADK (Agent Development Kit)

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **ADK** | Google's open-source framework for writing agents (Python, Java, Go, TypeScript) | ASP.NET for agents | 2 |
| **`LlmAgent` / `Agent`** | An agent driven by a model: name, instruction, tools | A controller class | 2 |
| **Workflow agents** | `SequentialAgent`, `ParallelAgent`, `LoopAgent`: a fixed order of steps with no LLM deciding it | A pipeline / SSIS package | 7 |
| **Sub-agents / `AgentTool`** | One agent hands control to another, or calls it as a tool | Calling another service | 7 |
| **Orchestrator** | The top agent that splits a task and delegates to specialist sub-agents | A controller calling services | 7 |
| **Transfer (LLM routing)** | With `sub_agents`, the model decides to hand the conversation to another agent | A router picking a handler at runtime | 7 |
| **Graph `Workflow`** (ADK 2.x) | Nodes and edges (with `JoinNode`, retries) for fixed multi-step flows; **verified** present in ADK 2.15 | Durable Functions orchestration | 7 |
| **`LangGraphAgent`** | Wraps a LangGraph graph as an ADK agent | An adapter | 7 (mention) |
| **Runner** | Runs an agent: feeds it messages, records events, executes tools | The ASP.NET host / middleware pipeline | 2 |
| **Session** | One conversation's history (events) plus its **state** dictionary | `HttpContext.Session` | 2 |
| **State** | Key-value data the agent and tools share; the prefixes `user:`, `app:` and `temp:` set its scope | Session or app cache | 2 |
| **Event** | One recorded step: user message, model reply, tool call, tool result | A row in an audit log | 2 |
| **Callback** | A hook before or after a model call or tool call, used to log, block or change it | Middleware / action filters | 9 |
| **ADK plugin (`BasePlugin`)** | A class registered once on the Runner/App whose callbacks run for every agent, model call and tool call in the app | Global middleware in `Program.cs` | 9 |
| **Tool confirmation (human in the loop)** | ADK pauses before a chosen tool runs and waits for a person to approve (**guess**: exact API to check) | An approval step in a workflow | 9 |
| **Artifact (ADK)** | A file the agent saves or loads during a session (not Artifact Registry) | A blob attached to the session | 3 |
| **`adk web` / `adk run` / `adk api_server`** | Local chat UI, terminal chat, and a local REST server | `dotnet run` with Swagger | 2 |
| **`adk eval` / evalset** | Runs saved test conversations and scores both the tool path and the answers | Unit and integration tests for the agent | 6 |

## Tools, MCP and skills

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **Tool / `FunctionTool`** | A Python function the model can call; ADK reads its signature and docstring | A public method with XML docs | 3 |
| **Toolset** | A group of tools loaded together, e.g. `McpToolset`, `BigQueryToolset` | A NuGet package of methods | 3 |
| **Built-in tools** | Tools that ship with ADK or Gemini: Google Search, code execution, BigQuery | BCL methods | 3 |
| **MCP (Model Context Protocol)** | An open protocol that lets any agent use tools and data from any server | ODBC/OLE DB for agent tools | 3 |
| **MCP host / client / server** | The host is the app (our agent), the client is its connection, and the server offers tools, resources and prompts | App / driver / database | 3 |
| **MCP transport: stdio vs Streamable HTTP** | stdio runs the server as a local child process; Streamable HTTP reaches a remote server over HTTPS. The Gemini Enterprise app needs Streamable HTTP (legacy SSE is not supported) | Named pipes vs TCP | 5 |
| **MCP tools / resources / prompts** | Tools are actions to call, resources are documents to read, prompts are reusable templates | Stored procs / views / snippets | 5 |
| **Remote (Google-managed) MCP server** | An MCP endpoint Google hosts, e.g. Knowledge Catalog at `https://dataplex.googleapis.com/mcp`; the caller needs `roles/mcp.toolUser` | Azure SQL vs your own SQL box | 3 |
| **MCP Toolbox for Databases** | Google's open-source MCP server that exposes SQL queries (BigQuery and others) as tools | A data-access layer | 3 (optional) |
| **FastMCP** | A Python library for writing your own MCP server in a few lines | Minimal APIs | 5 |
| **Agent Skill / `SKILL.md`** | A folder of instructions, plus optional `references/` and `scripts/`, that the agent loads only when needed. ADK loads it with `SkillToolset` | A runbook the agent opens on demand | 4 |
| **Progressive disclosure** | The agent sees only each skill's name and summary at first, and loads the full skill only when it needs it, which saves tokens | Lazy loading | 4 |
| **Skill vs MCP vs tool** | A skill is knowledge and steps (content); an MCP server is live capabilities over a protocol (a service); a tool is one function | Docs vs a service vs a method | 4 |
| **Skill Registry** (Preview) | A private, per-project store for uploading, versioning and sharing skills across agents | A private NuGet feed for content packages | 10 |
| **`agent-platform-skill-registry`** | A Google-published skill that teaches an agent to upload, update and list skills in Skill Registry | A CLI for the package feed | 10 |
| **Claude Code plugin** | A bundle of skills, MCP server configs, slash commands, hooks and sub-agents for Claude Code, shared through Git-based marketplaces | A VS Code extension pack | 10 (optional) |
| **Gemini CLI extension** | Google's equivalent for Gemini CLI: MCP servers, context files and commands, installed from Git or a gallery | Same idea, different tool | 10 (compare) |

## Agents talking to agents

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **A2A (Agent2Agent protocol)** | An open protocol for one agent to call another agent (not a tool) over HTTP | gRPC between microservices | 12 |
| **Agent card** | JSON describing an A2A agent: name, skills, endpoint, auth. Served at `/.well-known/agent-card.json` | OpenAPI / WSDL | 12 |
| **`RemoteA2aAgent`** | ADK's client for calling an A2A agent as if it were a local sub-agent | A generated service client | 12 |

## Google Cloud: Gemini Enterprise Agent Platform (formerly Vertex AI)

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **Gemini Enterprise Agent Platform** | Google's umbrella for building, scaling, governing and optimizing agents. Renamed from Vertex AI in April 2026 | Azure AI Foundry | 0 |
| **Agent Runtime** (formerly Agent Engine) | Managed hosting for agents: you deploy code, Google runs and scales it | Azure App Service / Functions | 8 |
| **Managed Agents** | Agents defined and run on the platform itself, which can mount registered skills under `/.agent/skills` | A hosted low-code app | 18 |
| **Sessions service** | Agent Runtime's managed storage for session history | Session state in SQL Server | 8 |
| **Memory Bank** | Long-term memory across sessions: it extracts facts about a user and recalls them later | A user profile table filled in automatically | 13 |
| **Agent Identity** | Each agent gets its own identity, a SPIFFE-style `principal://…` ID, and you grant IAM roles to it instead of to a shared service account | Managed Identity | 8–9 |
| **SPIFFE** | An open standard for workload identities; the format behind Agent Identity | X.509 cert identity | 9 |
| **Principal** | Anything IAM roles can be granted to: a user, group, service account or agent identity | A SQL login | 9 |
| **Agent Registry** | A central catalog of agents, MCP servers and (Preview) skills. Agents deployed to Agent Runtime are registered automatically | Service registry / NuGet feed | 10 |
| **Agent metadata** | What the registry holds about an agent: name, version, framework, capabilities, endpoint, agent card | A `.nuspec` | 10 |
| **Agent Gateway** | The networking layer that governs agent traffic. Agent Runtime routes outbound calls through it automatically | API Management | 11 |
| **Egress vs client-to-agent mode** | Egress governs calls *from* an agent to tools and agents; client-to-agent governs calls *into* an agent (not supported for Gemini Enterprise) | Outbound vs inbound firewall rules | 11 |
| **Egress policy** | Lets one agent principal call a destination. With IAP V2 (lesson 11) this is a **Unified Access Policy**; `roles/iap.egressor` alone does not open egress (**docs**) | Outbound firewall rule | 11 |
| **CEL condition** | Common Expression Language rule on a policy, e.g. `mcp.toolName == "lookup_entry"`, to allow or deny single MCP tools | A `WHERE` clause on permissions | 11 |
| **Permissive vs ENFORCED** | In permissive mode the gateway only logs what it would block; ENFORCED actually blocks | Audit mode vs deny mode | 11 |
| **Model Armor** | Content guardrails on prompts and responses (prompt injection, sensitive data); can run on Agent Gateway | A WAF for prompts | 11 |
| **Private Service Connect (PSC) / Cloud NAT** | Private network paths and a fixed outbound IP, used by some gateway setups | Private endpoints / NAT gateway | 11 (if needed) |
| **Gemini Enterprise** (the app) | Google's end-user agent app: you can publish agents to colleagues and connect MCP servers | Teams app store | 14 |
| **Agent Starter Pack / `agents-cli`** | Google templates and a CLI that scaffold an agent with CI/CD and Terraform | `dotnet new` templates | 19 (compare) |
| **Agent Garden** | A gallery of sample agents and tools | Sample gallery | 0 |
| **Agent Studio** | Low-code visual canvas for designing agents and workflows | Power Automate / Logic Apps designer | 18 |
| **Managed Agents API** (Preview) | Config-driven REST API: an Agents API (configuration, sandbox, mounted skills) plus an Interactions API (talking to the deployed agent) | Declarative YAML pipelines vs hand-written code | 18 |
| **Model Garden** | Catalog of Gemini, partner (Claude, Grok, Mistral) and open models (Llama, DeepSeek, Qwen) | Marketplace of engines | 0 |
| **Code Execution** | Sandbox where an agent writes and runs Python | A locked-down scratch VM | not used |
| **RAG Engine / Vector Search** | Connect documents to a model / vector index for semantic search | Full-text search, but by meaning | not used |
| **Share agent** | Share a deployed agent with other projects or organizations | Granting cross-tenant access | 10 |
| **Content security** | Monitors and filters agent inputs and outputs | Output encoding + DLP | 11 |
| **Semantic governance** | Policies about meaning (for example "never reveal city-level data"), to stop data leaking | Row-level security, but by meaning | 11 |
| **AI threat and vulnerability scanning** | Real-time threat detection for agent systems | Defender for Cloud | 20 |

## Knowledge layer (from the kc-okf POC)

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **Knowledge Catalog** (formerly Dataplex Universal Catalog) | Google's metadata catalog: entries, aspects, glossaries, context sets | SQL Server extended properties + Purview | 3 |
| **Context set** | A Knowledge Catalog entry group of curated pages written for agents | A wiki space for agents | 3 |
| **OKF (Open Knowledge Format)** | An open spec for agent-readable knowledge: Markdown plus YAML frontmatter | A documentation file format | 4 |
| **kcmd** | A CLI that pulls and pushes Knowledge Catalog context as files and serves it over MCP | `sqlpackage` for catalog docs | 5 (compare) |

## Delivery, security and operations

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **ADC (Application Default Credentials)** | How Google libraries find credentials: your gcloud login when running locally, the agent identity when deployed | `DefaultAzureCredential` | 1 |
| **IAM role binding** | Grants a principal a role on a resource | `GRANT` in SQL | 9 |
| **Cloud Build** | Google's CI/CD runner, driven by `cloudbuild.yaml` | Azure Pipelines | 19 |
| **Workload Identity Federation (WIF)** | Lets GitHub Actions or other outside systems act in GCP without key files | OIDC federated credentials | 19 |
| **Update vs re-create** | Redeploying into the same Agent Runtime resource vs creating a new one; affects the URL, registry entry and possibly the agent identity | In-place deploy vs new slot | 19 |
| **Cloud Run invoker / ID token** | IAM role that allows calling a private Cloud Run service; callers send a Google-signed ID token | Azure AD app role + bearer token | 5 |
| **Artifact Registry** | Stores container images and packages (not ADK artifacts) | Azure Container Registry | 5 |
| **Cloud Run** | Serverless containers; it hosts our MCP server | Azure Container Apps | 5 |
| **Terraform** | Infrastructure as code | Bicep / ARM | 19 (optional) |
| **OpenTelemetry / Cloud Trace / Cloud Logging** | Traces of each model and tool call, plus logs | Application Insights | 16 |
| **Staging bucket** | The Cloud Storage bucket where a deploy uploads the packaged agent | Build drop folder | 8 |

## Evaluation, observability and optimization

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **Offline evaluation** | Score the agent against a fixed test set (our 15 questions) | Regression test suite | 6 |
| **Simulated evaluation / user simulator** | Another LLM plays the user (with a persona) for several turns, then the conversation is scored | Load test with scripted users, but smart | 6 |
| **AutoRater / LLM-as-judge** | A model that scores answers against a rubric | A code reviewer bot | 6, 17 |
| **Online evaluation** | Judges score live production traffic continuously | Synthetic monitoring + quality alerts | 17 |
| **Prompt optimizer** | Reads failures and proposes better instructions and tool descriptions | Index tuning advisor, for prompts | 17 |
| **Unified Trace Viewer** | Google's view of an agent trace: each model and tool call as a span | Application Insights end-to-end transaction | 16 |
| **Topology** | A graph of the agent and everything it calls (models, tools, other agents) | Application Map | 16 |
| **Span / trace** | A trace is one request; a span is one step inside it, with timing and data | A row in a call tree | 16 |
| **LangSmith** | LangChain's hosted tracing, evaluation and prompt tool (works with any framework) | Third-party APM | 16 (compare) |
| **Langfuse** | Open-source, self-hostable alternative to LangSmith | Self-hosted Seq / Grafana | 16 |

## User interfaces

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **ADK dev UI (`adk web`)** | Local developer UI: chat, Events, Traces, State, Artifacts, Evals, agent graph. Not for production (no login) | Swagger UI + a debugger | 2 |
| **Web GUI** | A real front end for users that calls the deployed agent's query and stream API | A Blazor / React front end | 14 |
| **A2UI (Agent-to-User Interface)** | Google's open protocol (1.0, 2026-11-11): the agent sends declarative UI JSON, and the client renders it from an approved component catalog, so no agent code runs in the browser | Adaptive Cards / server-driven UI | 15 |
| **A2UI renderer** | Client library that draws A2UI JSON (web, Flutter, Android) | A view engine | 15 |
| **AG-UI** | CopilotKit's open protocol for streaming agent events (text, tool calls, state) to a front end | SignalR events for agents | 15 (compare) |
| **MCP Apps / `render_ui_widget`** | Interactive UI served by an MCP server; ADK's `tool_context.render_ui_widget(UiWidget)` attaches one to an event (**verified** in ADK 2.15 source) | An embedded iframe widget | 15 (compare) |

## Added after lessons 5 to 10 (verified in the lessons)

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **`output_key` / `{placeholder}`** | An agent saves its reply in session state under a name; the next agent's instruction reads it with `{name}` (`{name?}` = empty if missing) | Passing a DTO between steps | 7 |
| **`Workflow` (ADK 2.x)** | A graph of nodes and edges, with routes like `"approved"` / `"fix"`; replaces the deprecated `SequentialAgent`, `ParallelAgent` and `LoopAgent` | A state machine | 7 |
| **`AgentTool`** | Wraps an agent so another agent calls it like a function and stays in charge | Calling a service method | 7 |
| **`App` (ADK)** | Wraps the root agent and adds app-wide settings such as plugins; loaders look for `app` before `root_agent` | `Program.cs` | 9 |
| **Eval config** | Metrics, thresholds and judge model for an eval set (`test_config.json`): the eval set is the exam, the config the marking scheme | `.runsettings` | 6 |
| **Rubric** | A yes/no line a judge model checks; needs `"type": "FINAL_RESPONSE_QUALITY"` | An acceptance criterion | 6 |
| **Persona (simulated user)** | The kind of user a simulator plays (`NOVICE`, `EXPERT`); the simulator is graded too | A test persona | 6 |
| **`.agent_engine_config.json`** | Deploy settings next to an agent: `identity_type`, `min_instances`, `max_instances` | Hosting settings | 8 |
| **`principalSet`** | A group of principals, e.g. every agent in the project | An AD group | 9 |
| **Role / binding / scope** | A role is a set of permissions; a binding gives a principal a role on a resource; the scope is where it applies | Role + `[Authorize]` + where it's applied | 9 |
| **Least privilege** | The smallest roles on the smallest scope that work; grant one, read the error, grant the next | Minimal SQL grants | 9 |
| **401 vs 403** | 401: credentials not accepted. 403: known but not allowed | HTTP in ASP.NET | 9 |
| **mTLS** | Both sides show a certificate; a deployed agent's token is accepted only on `*.mtls.googleapis.com` hosts | Client-certificate auth | 9 |
| **GA vs Preview** | GA = stable and supported; Preview = early, may change | Release vs beta | 9 |
| **Registry service** | What you create to register your own agent, MCP server or endpoint in Agent Registry | Publishing a package | 10 |
| **Tool spec** | An MCP server's tool list stored with its registry entry (max 150 KB) | API docs on a package page | 10 |
| **Skill revision / state** | Each upload is a revision; a skill is Draft, Active, Disabled...; only Active skills download | Package versions | 10 |
| **`CUSTOM` registry entry** | How an auto-registered ADK agent appears: Agent Runtime URLs and identity, no agent card ("Non A2A") | A service with no API docs | 10 |
| **Implicit caching** | Gemini reuses a repeated prompt prefix by itself and bills it lower (`input_cached_tokens`) | A query plan cache | 5 |
| **IAP (Identity-Aware Proxy)** | The guard: checks who is calling against IAM's rules, at a door. Also guards web apps and SSH; V2 handles agent calls | An auth middleware | 11 |
| **Authz extension / authz policy** | The extension is the guard (IAP); the authz policy hooks it to a gateway ("this door uses this guard") | Middleware + its registration | 11 |
| **Unified Access Policy (UAP)** | The list the guard reads: ALLOW/DENY rules per agent principal and destination (host, or registered MCP server and tool) | Firewall rules per identity | 11 |
| **Default deny** | An enforced egress gateway blocks everything not allowed by a rule | A firewall with no rules | 11 |
| **DRY_RUN vs ENFORCED** | Dry run lets every call through and logs; enforced really blocks. In our test the dry run logged ALLOWED for everything | Report-only vs enforced | 11 |
| **Registered vs unregistered destination** | Registered = in the gateway's regional Agent Registry (tool-level rules possible); unregistered = a plain host (host/path rules only) | Known service vs raw URL | 11 |
| **Certificate-bound token** | A token that works only with the agent's own certificate (mTLS); turned off with a gateway (GOOGLE_API_ENABLE_RUNTIME_BOUND_TOKEN=false) | A token pinned to a client cert | 11 |
| **Memory Bank** | Agent Platform's long-term memory, part of an Agent Runtime instance: a model extracts short facts from conversations, kept per app and user, searched by meaning | A search index of notes about each user | 13 |
| **`preload_memory` vs `load_memory`** | preload: ADK searches memory before every Gemini call and adds the matches as a temporary message; load: a tool the model calls when it decides to | Eager vs lazy loading | 13 |
| **Memory scope** | The keys a memory belongs to (`app_name`, `user_id`); a later session with the same keys finds it | A tenant + user filter | 13 |
| **Consolidation** | Memory Bank merges a new fact with existing ones (update, not duplicate) | An upsert | 13 |
| **Explicit context caching** | ADK (`ContextCacheConfig` on `App`) asks Gemini to store the conversation's start and reuse it by ID, from turn 2; small storage fee | A prepared statement cache | 23 |
| **Cache hit / miss** | Hit: found in the cache, the real call is skipped. Miss: not there, the real call runs and the answer is saved | `TryGetValue` true / false | 23 |
| **Trim (tool result)** | Cut what a tool returns before the model sees it; not a cache. Here: drop MCP's duplicate `structuredContent` | DTO projection | 23 |
