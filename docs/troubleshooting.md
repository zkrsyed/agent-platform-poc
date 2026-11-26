# Troubleshooting and lessons learned

Every problem we hit in lessons 4 to 10, with its cause and fix. The same table is in `index.html` (Troubleshooting section).

| Lesson | Symptom | Cause | Fix |
|---|---|---|---|
| 4 | `429 RESOURCE_EXHAUSTED` from Gemini | Vertex rate limit or capacity on big (~35K-token) bursts; not credentials (tiny calls worked) | Wait and retry, run fewer things in parallel (`adk eval --parallelism 1`) |
| 4, 9, 10 | The README preview shows old text | The editor's Markdown preview didn't reload after the file changed | Close the preview tab and open it again (or open the file itself) |
| 5 | `jq: parse error` | The script printed Python dicts (single quotes, `False`), not JSON | Print the text parts, or use `json.dumps` |
| 5 | `ConnectionError: All connection attempts failed` | The HTTP MCP server wasn't running | Start the server first (terminal A), keep it running |
| 5 | The question went to the wrong agent in `adk web` | `adk web agents` lists every agent folder; the dropdown picks one (alphabetical first) | Choose the agent in the dropdown, then New Session |
| 6 | Rubric metric says `NOT_EVALUATED`, log: "Rubrics are required." | Each rubric needs a type the metric filters on | Add `"type": "FINAL_RESPONSE_QUALITY"` to each rubric |
| 6 | `adk eval` exits with an error code | One or more cases failed, like a test runner | Read the summary; `--print_detailed_results` for one case (`file.json:case_id`) |
| 6, 7 | A simulated or single run fails or passes "by luck" | Free text and model choices vary run to run; judges and simulators can be wrong too | Read the conversation; use `--num_runs 3` before deciding |
| 7 | The reviewer approved a wrong query | A reviewer is only as good as its checklist | Give it explicit checks (e.g. "GA4's built-in fields do NOT replace our definitions") |
| 7 | A pipeline step answered without the reason | Each Workflow step knows only what you pass it (state, instruction) | Pass the needed context, or give that step the skill |
| 8 | Deploy: "container failed to start" | The image installed only `google-adk[a2a]` (no `mcp`) | Read the container log (`gcloud logging read 'resource.labels.reasoning_engine_id="ID"'`); add `requirements.txt` |
| 8 | Secrets would be uploaded | `adk deploy` turns every line of the agent folder's `.env` into a cloud setting | Deploy a clean build folder (`scripts/stage_deploy.py`) |
| 8 | Skill missing when deployed | Only the agent folder is uploaded | Copy the skill into the build folder |
| 8 | `404 NOT_FOUND` for `gemini-3.5-flash` | The model is served only on `global`; `--region` sets `GOOGLE_CLOUD_LOCATION` | `Gemini(model=..., client_kwargs={"location": "global"})` |
| 8 | Console Traces / Dashboard empty; Sessions asks for App Hub | Deployed without `--otel_to_cloud`; `apphub.googleapis.com` off | Turn each on in its lesson (16, 13), after checking cost |
| 8, 16 | Topology: "A project owned by an organization is required" | Our project has no organization | Needs Cloud Identity / Workspace (a later decision) |
| 8 | The deployed agent retried 8 failing calls | Nothing told it to stop | Guardrail plugin: block tools after 3 errors in a turn (lesson 9) |
| 9, 10 | `400 INVALID_ARGUMENT`, empty log results, or `IndexError` in a script | A placeholder (`ID`, `NAME`) was sent literally | Set `ID=...` once and use `$ID`; scripts accept display names |
| 9 | "The member  is of an unknown type" (nothing between the spaces) | `$P` was empty: a new terminal tab | Run the `R=` / `P=` lines again in this tab |
| 9 | A `bq` job ran in another project | `bq` uses its own default project | Always pass `--project_id` |
| 9 | `grep principalSet` didn't show the new role | The role is on the single `principal://`, not the `principalSet` group | `grep reasoningEngines`, or the console IAM page |
| 9 | Catalog MCP: generic "Server returned an error response" | ADK hides the server's reply | Read the container log for the HTTP status |
| 9 | Catalog MCP: **401** on `dataplex.googleapis.com` | The deployed agent's token is accepted only on mTLS hosts (guess, fits the logs) | `CATALOG_MCP_URL=https://dataplex.mtls.googleapis.com/mcp` in the build's `.env` |
| 9 | Catalog MCP: **403** on `tools/call` only | Calling tools on Google MCP servers needs `mcp.tools.call` | Grant `roles/mcp.toolUser` |
| 9 | Still 403 right after a grant | IAM takes a few minutes to propagate | Wait; the admin audit log shows when each grant happened |
| 10 | Skill upload `400 ... type is required` | Required fields not in the docs page | Read the API's discovery document (`$discovery/rest?version=v1`): `type: SIMPLE`, `targetState` |
| 10 | `409 The resource is being created` | The skill was still being created | Wait; `targetState: ACTIVE` at creation makes `activate` unnecessary |
| 10 | The registry's MCP toolset offers write tools | `get_mcp_toolset` returns the whole server | Set `toolset.tool_filter = [...]` afterwards |

## Lessons learned

- Measure, don't eyeball: the same eval set compared one agent, a team and a pipeline (lessons 6–7).
- One run proves little: run 3 times before ranking (lessons 4, 6, 7).
- Skill = advice the model usually follows; IAM = what it can reach; plugin = rules it can't skip; Gateway (lesson 11) = rules on the network.
- Least privilege is a loop: grant one role, read the error, grant the next (lesson 9).
- 401 = credentials not accepted; 403 = known but not allowed.
- When something fails in the cloud, read the logs: the container log and the audit log told us every cause.
- Carry vs look up: a copied skill drifts; a live page or registry entry stays current but must be reachable (lessons 5, 10).
- Before putting anything in a public repo, check it for secrets, emails and project numbers (screenshots too).
