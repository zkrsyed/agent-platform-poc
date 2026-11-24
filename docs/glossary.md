# Glossary

Every term this POC touches, explained in one line with a .NET or SQL Server comparison where one helps. "Lesson" says where you first use it. Unless marked otherwise, each entry is **docs** (from Google's docs or a spec) until a lesson verifies it.

## Agent basics

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **Agent** | A program that loops: the LLM reads the context, picks a tool, sees the result and repeats until it can answer | A controller whose logic is decided at runtime by a model | 0 |
| **Context engineering** | Choosing what the model sees: instructions, tool results, docs, memory | Building the right query plan inputs | 0 |
| **Grounding** | Making answers rely on real sources (catalog, data) rather than the model's memory | Joining to the source of truth instead of guessing | 3 |
| **Prompt injection** | Text in data or tool output that tries to give the agent instructions | SQL injection, but in natural language | 8 |

## ADK (Agent Development Kit)

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **ADK** | Google's open-source framework for writing agents (Python, Java, Go, TypeScript) | ASP.NET for agents | 2 |
| **`LlmAgent` / `Agent`** | An agent driven by a model, with a name, instruction and tools | A controller class | 2 |
| **Workflow agents** | `SequentialAgent`, `ParallelAgent`, `LoopAgent`: fixed orchestration with no LLM deciding the order | A pipeline or SSIS package | 9 |
| **Sub-agents / `AgentTool`** | One agent calls another, either by handing over control or as a tool | Calling another service | 9 |
| **Runner** | Runs an agent: feeds it messages, records events and handles tools | The ASP.NET host / middleware pipeline | 2 |
| **Session** | One conversation's history (events) plus its **state** dictionary | `HttpContext.Session` | 2 |
| **State** | Key-value data the agent and tools share during a session (`user:`, `app:` and `temp:` prefixes set the scope) | Session or app cache | 2 |
| **Event** | One recorded step: a user message, a model reply, a tool call or a tool result | A row in an audit log | 2 |
| **Callback** | A hook before or after a model or tool call, used to log, block or change it | Middleware / action filters | 8 |
| **Artifact (ADK)** | A file the agent saves or loads during a session (not the same as Artifact Registry) | A blob attached to the session | 3 |
| **`adk web` / `adk run` / `adk api_server`** | Local chat UI, terminal chat and local REST server | `dotnet run` with Swagger | 2 |
| **`adk eval` / evalset** | Runs saved test conversations and scores the tool path and the answers | Unit and integration tests for the agent | 6 |

## Tools, MCP and skills

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **Tool / `FunctionTool`** | A Python function the model can call; ADK reads its signature and docstring | A public method with XML docs | 3 |
| **Toolset** | A group of tools loaded together, such as `McpToolset` or `BigQueryToolset` | A NuGet package of methods | 3 |
| **Built-in tools** | Tools that ship with ADK or Gemini: Google Search, code execution, BigQuery | BCL methods | 3 |
| **MCP (Model Context Protocol)** | An open protocol that lets any agent use tools and data from any server | ODBC/OLE DB for agent tools | 3 |
| **MCP host / client / server** | Host = the app (our agent). Client = its connection. Server = the thing that offers tools, resources and prompts | App / driver / database | 3 |
| **MCP transport: stdio vs Streamable HTTP** | stdio means a local child process; Streamable HTTP means a remote server reached over HTTPS | Named pipes vs TCP | 5 |
| **MCP tools / resources / prompts** | Actions to call, documents to read, and reusable prompt templates | Stored procs / views / snippets | 5 |
| **Remote (Google-managed) MCP server** | An MCP endpoint Google hosts, such as Knowledge Catalog at `https://dataplex.googleapis.com/mcp`. The caller needs `roles/mcp.toolUser` | Azure SQL vs your own SQL box | 3 |
| **MCP Toolbox for Databases** | Google's open-source MCP server that exposes SQL queries (BigQuery and others) as tools | A data-access layer | 3 (optional) |
| **FastMCP** | A Python library for writing your own MCP server in a few lines | Minimal APIs | 5 |
| **Agent Skill / `SKILL.md`** | A folder of instructions plus optional `references/` and `scripts/` that the agent loads only when it needs it. ADK loads one with `SkillToolset` | A plugin or a runbook the agent opens on demand | 4 |
| **Progressive disclosure** | The agent sees only each skill's name and summary at first and loads the full text when it needs it, which saves tokens | Lazy loading | 4 |
| **Skill vs MCP vs tool** | A skill holds knowledge and steps; an MCP server provides live capabilities over a protocol; a tool is a single function | Docs vs a service vs a method | 4 |

## Agents talking to agents

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **A2A (Agent2Agent protocol)** | An open protocol for one agent to call another agent (not a tool) over HTTP | gRPC between microservices | 9 |
| **Agent card** | A JSON description of an A2A agent (name, skills, endpoint, auth), served at `/.well-known/agent-card.json` | An OpenAPI or WSDL document | 9 |
| **`RemoteA2aAgent`** | ADK's client for calling an A2A agent as if it were a local sub-agent | A generated service client | 9 |

## Google Cloud: Gemini Enterprise Agent Platform (formerly Vertex AI)

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **Gemini Enterprise Agent Platform** | Google's umbrella for building, scaling, governing and optimizing agents. Renamed from Vertex AI in April 2026 | Azure AI Foundry | 0 |
| **Agent Runtime** (formerly Agent Engine) | Managed hosting for agents; you deploy code, Google runs and scales it | Azure App Service / Functions | 7 |
| **Sessions service** | Agent Runtime's managed storage for session history | Session state in SQL Server | 7 |
| **Memory Bank** | Long-term memory across sessions: it extracts facts about a user and recalls them later | A user profile table filled in automatically | 10 |
| **Agent Identity** | A per-agent identity, a SPIFFE-style `principal://…` ID, that you grant IAM roles to instead of a shared service account | Managed Identity | 7–8 |
| **SPIFFE** | An open standard for workload identities; the format behind Agent Identity | X.509 certificate identity | 8 |
| **Principal** | Anyone or anything that can be granted IAM roles: a user, a group, a service account or an agent identity | A SQL login | 8 |
| **Agent Registry** | A central catalog of agents and MCP servers (yours, Google's and third-party). Agents deployed to Agent Runtime are registered automatically | A service registry or NuGet feed | 9 |
| **Agent metadata** | What the registry holds about an agent: name, version, framework, capabilities, endpoint, agent card | A `.nuspec` file | 9 |
| **Agent Gateway** | The networking layer that governs traffic between agents and their destinations (MCP servers, other agents, APIs) | An API gateway such as APIM | 8 |
| **Model Armor** | Content guardrails on prompts and responses (prompt injection, sensitive data). It can run on Agent Gateway | A WAF for prompts | 8 |
| **Gemini Enterprise** (the app) | Google's end-user agent app; you can publish your agent there for colleagues | Teams app store | 12 (optional) |
| **Agent Starter Pack / `agents-cli`** | Google templates and a CLI that scaffold an agent along with CI/CD and Terraform | `dotnet new` templates | 11 (compare) |
| **Agent Garden** | A gallery of sample agents and tools | Sample gallery | 0 |

## Knowledge layer (from the kc-okf POC)

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **Knowledge Catalog** (formerly Dataplex Universal Catalog) | Google's metadata catalog: entries, aspects, glossaries, context sets | SQL Server extended properties + Purview | 3 |
| **Context set** | A Knowledge Catalog entry group holding curated pages written for agents | A wiki space for agents | 3 |
| **OKF (Open Knowledge Format)** | An open spec for agent-readable knowledge as Markdown with YAML frontmatter | A documentation file format | 4 |
| **kcmd** | A CLI that pulls or pushes Knowledge Catalog context as files, and serves it over MCP | `sqlpackage` for catalog docs | 5 (compare) |

## Delivery, security and operations

| Term | What it is | Compare to | Lesson |
|---|---|---|---|
| **ADC (Application Default Credentials)** | How Google libraries find credentials: your gcloud login locally, the agent identity when deployed | `DefaultAzureCredential` | 1 |
| **IAM role binding** | Grants a principal a role on a resource | `GRANT` in SQL | 8 |
| **Cloud Build** | Google's CI/CD runner, driven by `cloudbuild.yaml` | Azure Pipelines | 11 |
| **Workload Identity Federation (WIF)** | Lets GitHub Actions (or another external system) act in GCP without key files | OIDC federated credentials | 11 |
| **Artifact Registry** | Stores container images and packages (not the same as ADK artifacts) | Azure Container Registry | 5 |
| **Cloud Run** | Serverless containers; we host our own MCP server there | Azure Container Apps | 5 |
| **Terraform** | Infrastructure as code | Bicep / ARM | 11 (optional) |
| **OpenTelemetry / Cloud Trace / Cloud Logging** | Traces of each model and tool call, plus logs | Application Insights | 12 |
| **Staging bucket** | A Cloud Storage bucket where deploys upload the packaged agent | Build drop folder | 7 |
