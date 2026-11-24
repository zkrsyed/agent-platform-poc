# Lesson 1: Setup

**Goal:** a Python project with ADK installed, gcloud and Application Default Credentials (ADC) pointing at the right project, the APIs we need on, and one test call to Gemini that works. About 20 minutes.

**Cost:** one tiny Gemini call (a fraction of a cent). Enabling APIs is free.

## The ideas

| Idea | One line | .NET comparison |
|---|---|---|
| **uv** | A fast Python package and project manager: creates `.venv`, writes `pyproject.toml` and `uv.lock` | `dotnet` CLI + NuGet + `packages.lock.json` |
| **`google-adk`** | The Agent Development Kit. Its *extras* (`[a2a,mcp,…]`) pull in optional pieces | A NuGet package with optional sub-packages |
| **`google-cloud-aiplatform`** | The "Agent Platform SDK for Python" (`import vertexai`). It deploys to Agent Runtime and talks to sessions, memory and so on. The name still says aiplatform even after the rename | Azure SDK management library |
| **gcloud configuration** | A named profile: account + project + region. We use `kc-okf` | `az account set` |
| **ADC** | The credential that *libraries* use, separate from the gcloud CLI login. Locally it's you; on Agent Runtime it's the agent's identity | `DefaultAzureCredential` |
| **Quota project** | The project that is billed and rate-limited for API calls made with ADC | The subscription an API call counts against |
| **API (service) enablement** | Each Google service must be switched on per project before it can be called | Registering a resource provider in Azure |

## What you'll have at the end

```
agent-platform-poc/
  pyproject.toml   ← new: project + dependencies
  uv.lock          ← new: exact versions (commit this)
  .venv/           ← new: git-ignored
```

---

## Step 1. Go to the repo and select the gcloud profile

```bash
cd ~/apps/agent-platform-poc
```

```bash
export CLOUDSDK_ACTIVE_CONFIG_NAME=kc-okf
```

```bash
gcloud config list
```

**Look for:** `project = kc-okf-poc-261122` and your account. If the project is different, stop and tell me.

The `export` only applies to this terminal. Run it again in every new terminal you use for this POC.

## Step 2. Check that ADC works and which quota project it uses

```bash
gcloud auth application-default print-access-token > /dev/null && echo "ADC ok"
```

```bash
grep quota_project_id ~/.config/gcloud/application_default_credentials.json
```

**Look for:** `ADC ok`, and `"quota_project_id": "kc-okf-poc-261122"`. It should already be set from the kc-okf POC.

If the first command fails, log in again. This opens a browser:

```bash
gcloud auth application-default login
```

If the quota project is something else, set it:

```bash
gcloud auth application-default set-quota-project kc-okf-poc-261122
```

> Why two logins? `gcloud auth login` is for the **CLI**. `application-default login` writes a separate file that **libraries** (ADK, the Python SDK) read. In .NET terms, signing in to `az` doesn't automatically mean your app's `DefaultAzureCredential` uses the same account in every case.

## Step 3. See which APIs are already on

```bash
gcloud services list --enabled --format="value(config.name)" | sort
```

**Look for** these three. They were probably enabled during kc-okf:

| API | Used for | First lesson |
|---|---|---|
| `aiplatform.googleapis.com` | Gemini models and everything on Agent Platform (Runtime, Sessions, Memory Bank, eval) | 2 |
| `dataplex.googleapis.com` | Knowledge Catalog, which also turns on its remote MCP server | 3 |
| `bigquery.googleapis.com` | Running SQL on `ga4_sample.events` | 3 |

Enable any of the three that are missing. Run it even if all three are there; it's harmless:

```bash
gcloud services enable aiplatform.googleapis.com dataplex.googleapis.com bigquery.googleapis.com
```

We **won't** turn on the other APIs yet. Each later lesson turns on its own, so you see which feature needs which service:

| Lesson | APIs (expected; we confirm names when we get there) |
|---|---|
| 5 | Cloud Run, Artifact Registry, Cloud Build (for the MCP server image) |
| 8 | Cloud Storage (staging bucket), Cloud Trace / Telemetry, Cloud Logging |
| 10 | Agent Registry (**guess**: name to check) |
| 11 | Agent Gateway / IAP / Model Armor (**guess**: names to check) |
| 14 | Cloud Run + IAP or Identity Platform (web GUI login, **guess**) |
| 19 | Cloud Build, IAM Credentials (for WIF) |

## Step 4. Create the Python project

```bash
uv init --bare --python 3.12
```

This writes only `pyproject.toml`: no sample code and no git changes.

Now add the two packages. Keep the quotes: without them, zsh treats `>=` as "redirect to a file".

```bash
uv add "google-adk[a2a,agent-identity,mcp,eval]" "google-cloud-aiplatform[agent_engines,adk]>=1.112"
```

What the extras are for:

| Extra | Gives you | Lesson |
|---|---|---|
| `mcp` | `McpToolset`, the MCP client | 3, 5 |
| `eval` | `adk eval` scoring | 6 |
| `agent-identity` | Agent Identity / Agent Registry auth helpers (the docs ask for ADK ≥ 1.29 with this extra) | 8–10 |
| `a2a` | Agent2Agent client and server | 12 |
| `agent_engines`, `adk` (on aiplatform) | Deploy to Agent Runtime, `AdkApp` wrapper | 8 |

**If `uv add` fails** because the two packages want different `google-adk` versions, copy the error to me. Don't try to fix it by hand. A clash like that is a real finding to record.

## Step 5. Check the install

```bash
uv run adk --version
```

```bash
uv pip list | grep -Ei "google-adk|google-cloud-aiplatform|google-genai|mcp|a2a"
```

**Look for:** a `google-adk` version of 2.x. PyPI showed 2.15.0 on 2026-11-24 (**verified** on PyPI, not yet on your machine). Write down the versions; they go into the results file.

```bash
uv run adk --help
```

**Look for** the subcommands. You'll use `create`, `run`, `web`, `eval` and `deploy` later.

## Step 6. One test call to Gemini through Vertex (Agent Platform)

This proves that ADC, the project, the API and the model all work, before any agent code is involved.

```bash
uv run python -c "from google import genai; c = genai.Client(vertexai=True, project='kc-okf-poc-261122', location='global'); print(c.models.generate_content(model='gemini-3.5-flash', contents='Reply with exactly: setup ok').text)"
```

**Look for:** `setup ok`.

- `location='global'`: in kc-okf, `gemini-3.5-flash` worked **only** on `global`, not `us-central1` (**verified** in kc-okf).
- `vertexai=True` means "use Google Cloud with my ADC". The other way is an AI Studio API key (`GOOGLE_API_KEY`). ADK's own quickstart uses the key; we don't, because Agent Identity, IAM and audit logs only apply on the Google Cloud path.
- A `429 RESOURCE_EXHAUSTED` here is the quota throttling we saw in kc-okf. Wait a minute and retry.

## Step 7. Look in the console (optional, 2 minutes)

The API's page is **not** on the "Welcome to Gemini Platform" home page. That page is the product console. The API page lives under **APIs & Services**. Go there directly:

https://console.cloud.google.com/apis/api/aiplatform.googleapis.com/metrics?project=kc-okf-poc-261122

Or click through: ☰ menu → **APIs & Services** → **Enabled APIs & services**, then search for `aiplatform`. Its display name may be "Vertex AI API" or a new Agent Platform name, but the service name `aiplatform.googleapis.com` hasn't changed (**verified** in Step 3).

On the **Metrics** tab, within a few minutes you should see the request from Step 6, broken down by method (`GenerateContent`). This is the first place your agent's traffic shows up.

| Console place | What it is | .NET comparison |
|---|---|---|
| **Gemini Platform home** (where you land) | The product UI: Agent Studio, models, agents, guides | Azure AI Foundry portal |
| **APIs & Services → the API page** | The switch that turns the service on, plus its traffic, errors and quotas | Resource provider + API metrics in the Azure portal |

---

## Check yourself

1. What's the difference between `gcloud auth login` and `gcloud auth application-default login`, and which one does ADK use?
2. Why do we use `vertexai=True` and not an API key, given that we want to learn about Agent Identity?
3. Why does each later lesson turn on its own APIs instead of turning them all on now?

## Send me back

Paste these, and I'll write `results/01-setup.md` and mark the lesson done:

- the output of Step 5's `uv pip list | grep …`
- the Step 6 reply, or the error
- anything that surprised you or didn't match this page
