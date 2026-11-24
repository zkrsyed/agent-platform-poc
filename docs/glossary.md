# Glossary

Every term this POC touches, explained in one line with a .NET or SQL Server comparison where one helps. "Lesson" is where you first use the term. Each entry is **docs** (from Google's docs or a spec) until a lesson verifies it.

## Agent basics

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **Agent** | A program that loops: the LLM reads the context, picks a tool, sees the result, and repeats until it can answer | A controller whose logic is decided at runtime by a model | 0 |
| **Context engineering** | Choosing what the model sees: instructions, tool results, docs, memory | Building the right query plan inputs | 0 |
| **Grounding** | Making answers rely on real sources (the catalog, the data) rather than the model's memory | Joining to the source of truth instead of guessing | 3 |
| **Prompt injection** | Text in data or tool output that tries to give the agent instructions | SQL injection, but in natural language | 10 |

## ADK (Agent Development Kit)

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **ADK** | Google's open-source framework for writing agents (Python, Java, Go, TypeScript) | ASP.NET for agents | 2 |
| **`LlmAgent` / `Agent`** | An agent driven by a model: name, instruction, tools | A controller class | 2 |
| **Workflow agents** | `SequentialAgent`, `ParallelAgent`, `LoopAgent`: a fixed order of steps with no LLM deciding it | A pipeline / SSIS package | 11 |
| **Sub-agents / `AgentTool`** | One agent hands control to another, or calls it as a tool | Calling another service | 11 |
| **Runner** | Runs an agent: feeds it messages, records events, executes tools | The ASP.NET host / middleware pipeline | 2 |
| **Session** | One conversation's history (events) plus its **state** dictionary | `HttpContext.Session` | 2 |
| **State** | Key-value data the agent and tools share; the prefixes `user:`, `app:` and `temp:` set its scope | Session or app cache | 2 |
| **Event** | One recorded step: user message, model reply, tool call, tool result | A row in an audit log | 2 |
| **Callback** | A hook before or after a model call or tool call, used to log, block or change it | Middleware / action filters | 8 |
| **ADK plugin (`BasePlugin`)** | A class registered once on the Runner/App whose callbacks run for every agent, model call and tool call in the app | Global middleware in `Program.cs` | 8 |
| **Tool confirmation (human in the loop)** | ADK pauses before a chosen tool runs and waits for a person to approve (**guess**: exact API to check) | An approval step in a workflow | 8 |
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
| **Skill Registry** (Preview) | A private, per-project store for uploading, versioning and sharing skills across agents | A private NuGet feed for content packages | 9 |
| **`agent-platform-skill-registry`** | A Google-published skill that teaches an agent to upload, update and list skills in Skill Registry | A CLI for the package feed | 9 |
| **Claude Code plugin** | A bundle of skills, MCP server configs, slash commands, hooks and sub-agents for Claude Code, shared through Git-based marketplaces | A VS Code extension pack | 9 (optional) |
| **Gemini CLI extension** | Google's equivalent for Gemini CLI: MCP servers, context files and commands, installed from Git or a gallery | Same idea, different tool | 9 (compare) |

## Agents talking to agents

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **A2A (Agent2Agent protocol)** | An open protocol for one agent to call another agent (not a tool) over HTTP | gRPC between microservices | 11 |
| **Agent card** | JSON describing an A2A agent: name, skills, endpoint, auth. Served at `/.well-known/agent-card.json` | OpenAPI / WSDL | 11 |
| **`RemoteA2aAgent`** | ADK's client for calling an A2A agent as if it were a local sub-agent | A generated service client | 11 |

## Google Cloud: Gemini Enterprise Agent Platform (formerly Vertex AI)

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **Gemini Enterprise Agent Platform** | Google's umbrella for building, scaling, governing and optimizing agents. Renamed from Vertex AI in April 2026 | Azure AI Foundry | 0 |
| **Agent Runtime** (formerly Agent Engine) | Managed hosting for agents: you deploy code, Google runs and scales it | Azure App Service / Functions | 7 |
| **Managed Agents** | Agents defined and run on the platform itself, which can mount registered skills under `/.agent/skills` | A hosted low-code app | 15 |
| **Sessions service** | Agent Runtime's managed storage for session history | Session state in SQL Server | 7 |
| **Memory Bank** | Long-term memory across sessions: it extracts facts about a user and recalls them later | A user profile table filled in automatically | 12 |
| **Agent Identity** | Each agent gets its own identity, a SPIFFE-style `principal://…` ID, and you grant IAM roles to it instead of to a shared service account | Managed Identity | 7–8 |
| **SPIFFE** | An open standard for workload identities; the format behind Agent Identity | X.509 cert identity | 8 |
| **Principal** | Anything IAM roles can be granted to: a user, group, service account or agent identity | A SQL login | 8 |
| **Agent Registry** | A central catalog of agents, MCP servers and (Preview) skills. Agents deployed to Agent Runtime are registered automatically | Service registry / NuGet feed | 9 |
| **Agent metadata** | What the registry holds about an agent: name, version, framework, capabilities, endpoint, agent card | A `.nuspec` | 9 |
| **Agent Gateway** | The networking layer that governs agent traffic. Agent Runtime routes outbound calls through it automatically | API Management | 10 |
| **Egress vs client-to-agent mode** | Egress governs calls *from* an agent to tools and agents; client-to-agent governs calls *into* an agent (not supported for Gemini Enterprise) | Outbound vs inbound firewall rules | 10 |
| **Egress policy** | An IAM-style policy that lets a given agent principal call a destination (role `roles/iap.egressor`) | A firewall rule tied to an identity | 10 |
| **CEL condition** | Common Expression Language rule on a policy, e.g. `mcp.toolName == "lookup_entry"`, to allow or deny single MCP tools | A `WHERE` clause on permissions | 10 |
| **Permissive vs ENFORCED** | In permissive mode the gateway only logs what it would block; ENFORCED actually blocks | Audit mode vs deny mode | 10 |
| **Model Armor** | Content guardrails on prompts and responses (prompt injection, sensitive data); can run on Agent Gateway | A WAF for prompts | 10 |
| **Private Service Connect (PSC) / Cloud NAT** | Private network paths and a fixed outbound IP, used by some gateway setups | Private endpoints / NAT gateway | 10 (if needed) |
| **Gemini Enterprise** (the app) | Google's end-user agent app: you can publish agents to colleagues and connect MCP servers | Teams app store | 9 (optional) |
| **Agent Starter Pack / `agents-cli`** | Google templates and a CLI that scaffold an agent with CI/CD and Terraform | `dotnet new` templates | 16 (compare) |
| **Agent Garden** | A gallery of sample agents and tools | Sample gallery | 0 |
| **Agent Studio** | Low-code visual canvas for designing agents and workflows | Power Automate / Logic Apps designer | 15 |
| **Managed Agents API** (Preview) | Config-driven REST API: an Agents API (configuration, sandbox, mounted skills) plus an Interactions API (talking to the deployed agent) | Declarative YAML pipelines vs hand-written code | 15 |
| **Model Garden** | Catalog of Gemini, partner (Claude, Grok, Mistral) and open models (Llama, DeepSeek, Qwen) | Marketplace of engines | 0 |
| **Code Execution** | Sandbox where an agent writes and runs Python | A locked-down scratch VM | not used |
| **RAG Engine / Vector Search** | Connect documents to a model / vector index for semantic search | Full-text search, but by meaning | not used |
| **Share agent** | Share a deployed agent with other projects or organizations | Granting cross-tenant access | 9 |
| **Content security** | Monitors and filters agent inputs and outputs | Output encoding + DLP | 10 |
| **Semantic governance** | Policies about meaning (for example "never reveal city-level data"), to stop data leaking | Row-level security, but by meaning | 10 |
| **AI threat and vulnerability scanning** | Real-time threat detection for agent systems | Defender for Cloud | 17 |

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
| **IAM role binding** | Grants a principal a role on a resource | `GRANT` in SQL | 8 |
| **Cloud Build** | Google's CI/CD runner, driven by `cloudbuild.yaml` | Azure Pipelines | 16 |
| **Workload Identity Federation (WIF)** | Lets GitHub Actions or other outside systems act in GCP without key files | OIDC federated credentials | 16 |
| **Update vs re-create** | Redeploying into the same Agent Runtime resource vs creating a new one; affects the URL, registry entry and possibly the agent identity | In-place deploy vs new slot | 16 |
| **Cloud Run invoker / ID token** | IAM role that allows calling a private Cloud Run service; callers send a Google-signed ID token | Azure AD app role + bearer token | 5 |
| **Artifact Registry** | Stores container images and packages (not ADK artifacts) | Azure Container Registry | 5 |
| **Cloud Run** | Serverless containers; it hosts our MCP server | Azure Container Apps | 5 |
| **Terraform** | Infrastructure as code | Bicep / ARM | 16 (optional) |
| **OpenTelemetry / Cloud Trace / Cloud Logging** | Traces of each model and tool call, plus logs | Application Insights | 13 |
| **Staging bucket** | The Cloud Storage bucket where a deploy uploads the packaged agent | Build drop folder | 7 |

## Evaluation, observability and optimization

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **Offline evaluation** | Score the agent against a fixed test set (our 15 questions) | Regression test suite | 6 |
| **Simulated evaluation / user simulator** | Another LLM plays the user (with a persona) for several turns, then the conversation is scored | Load test with scripted users, but smart | 6 |
| **AutoRater / LLM-as-judge** | A model that scores answers against a rubric | A code reviewer bot | 6, 14 |
| **Online evaluation** | Judges score live production traffic continuously | Synthetic monitoring + quality alerts | 14 |
| **Prompt optimizer** | Reads failures and proposes better instructions and tool descriptions | Index tuning advisor, for prompts | 14 |
| **Unified Trace Viewer** | Google's view of an agent trace: each model and tool call as a span | Application Insights end-to-end transaction | 13 |
| **Topology** | A graph of the agent and everything it calls (models, tools, other agents) | Application Map | 13 |
| **Span / trace** | A trace is one request; a span is one step inside it, with timing and data | A row in a call tree | 13 |
| **LangSmith** | LangChain's hosted tracing, evaluation and prompt tool (works with any framework) | Third-party APM | 13 (compare) |
| **Langfuse** | Open-source, self-hostable alternative to LangSmith | Self-hosted Seq / Grafana | 13 |
