# Lesson 1 results: Setup

Run on 2026-11-24. Everything on this page is **verified** unless marked otherwise.

## What worked

| Check | Result |
|---|---|
| gcloud profile `kc-okf` | `project = kc-okf-poc-261122`, region `us-central1` |
| ADC | Token printed; `quota_project_id` = `kc-okf-poc-261122` |
| APIs needed now | `aiplatform`, `dataplex`, `bigquery` were already enabled from kc-okf, so nothing new was turned on |
| `uv init --bare --python 3.12` | Wrote only `pyproject.toml` (`requires-python = ">=3.12"`) |
| `uv add …` | Resolved 139 packages and installed 134 in about 15 s. No version clash between `google-adk` and `google-cloud-aiplatform[adk]` |
| Gemini through Google Cloud | `gemini-3.5-flash` on `location='global'` replied `setup ok` |

## Versions installed

| Package | Version | Note |
|---|---|---|
| `google-adk` | 2.15.0 | Latest on PyPI that day |
| `google-cloud-aiplatform` | 2.10.0 | We asked for `>=1.112` (the docs' minimum) and got a 2.x major version |
| `google-genai` | 2.34.0 | The low-level Gemini client that ADK uses |
| `mcp` / `mcp-types` | 2.3.0 | MCP Python SDK (from the `mcp` extra) |
| `a2a-sdk` | 1.3.1 | From the `a2a` extra |
| `google-cloud-agentidentitycredentials`, `google-cloud-iamconnectorcredentials` | 0.1.2 | From the `agent-identity` extra: credential helpers for Agent Identity |
| `gepa` | 0.1.4 | Prompt optimizer used by `adk optimize` |
| `litellm` | 1.109.4 | Lets ADK call non-Google models |
| `opentelemetry-*` | 1.45.2 | Tracing, installed even without the `otel-gcp` extra |

`uv` rewrote the extra `agent_engines` as `agent-engines` in `pyproject.toml` (name normalisation; same thing).

## Things worth noticing

1. **`apptopology.googleapis.com`, `cloudtrace`, `telemetry` and `logging` were already enabled.** We didn't turn them on in this POC. They were probably switched on with Agent Platform or during kc-okf (**guess**). App Topology is likely what draws the Topology view in lesson 13 (**guess**).
2. **The ADK CLI has more than the docs' quickstart shows.** `adk --help` lists `api_server`, `conformance`, `create`, `deploy`, `eval`, `eval_set`, `generate_agent_card`, `migrate`, `optimize`, `run`, `telemetry`, `test`, `web`. Three map straight onto later lessons:
   - `adk optimize`: "Optimizes the root agent instructions using the GEPA optimizer". This is a local prompt optimizer to compare with Google's managed one in lesson 14.
   - `adk generate_agent_card`: builds A2A agent cards (lesson 11).
   - `adk eval_set` / `adk test`: manage evalsets and run tests (lesson 6).
3. **Install size:** 134 packages, including pandas, scikit-learn, scipy and boto3, mostly from the `eval` extra and litellm. This affects deploy package size in lesson 7 (**guess**).

## Questions this raises (to check later)

- Does Agent Runtime install `google-cloud-aiplatform` 2.x on deploy, or the `>=1.112` that the docs pin? (lesson 7)
- Is `apptopology` the API behind the Topology view? (lesson 13)
