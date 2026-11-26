# Cloud resources created by this POC

Every resource created in project `kc-okf-poc-261122` goes here, along with the lesson that made it and the command that removes it. Updated 2026-11-26 after lesson 10. Run the commands from the repo folder; every delete changes the cloud, so ask first.

Set these once per terminal tab (the agent's ID is the long number at the end of its resource name):

```bash
ID=7105399555822190592
R=projects/kc-okf-poc-261122/locations/us-central1/reasoningEngines/$ID
P=$(uv run python scripts/runtime.py principal $R)   # before deleting the agent
```

| Lesson | Resource | Name / ID | Cost while idle | Delete with |
|---|---|---|---|---|
| 8 | Agent Runtime instance (deployed agent, agent identity) | `ga4-guide`, `.../us-central1/reasoningEngines/7105399555822190592` | none while the scaling feature is in Preview (**docs**); `min_instances` 0 | `uv run python scripts/runtime.py delete $R` (also deletes its sessions) |
| 8 | Container image and build for the agent | managed by Agent Runtime (**guess**: no image in our Artifact Registry) | storage, cents at most (**guess**) | goes with the instance (**to check** at clean-up) |
| 9 | Project IAM bindings for the agent's principal | `bigquery.jobUser`, `dataplex.catalogViewer`, `serviceusage.serviceUsageConsumer`, `mcp.toolUser` | free | `for r in bigquery.jobUser dataplex.catalogViewer serviceusage.serviceUsageConsumer mcp.toolUser; do gcloud projects remove-iam-policy-binding kc-okf-poc-261122 --member="$P" --role="roles/$r" --condition=None; done` |
| 9 | Dataset IAM grant | `roles/bigquery.dataViewer` on `ga4_sample` | free | ``bq query --project_id=kc-okf-poc-261122 --use_legacy_sql=false "REVOKE \`roles/bigquery.dataViewer\` ON SCHEMA \`kc-okf-poc-261122.ga4_sample\` FROM \"$P\""`` |
| 10 | Enabled API | `agentregistry.googleapis.com` | free (registry operations are $0, **docs**) | `gcloud services disable agentregistry.googleapis.com --project kc-okf-poc-261122` (after deleting the two entries below) |
| 10 | Registry service (our MCP server's entry) | `okf-pages` (global) | free | `gcloud agent-registry services delete okf-pages --project kc-okf-poc-261122 --location global` |
| 10 | Registry skill | `private-ga4-context` (global), scanning `DISABLED` | free | ``curl -X DELETE -H "Authorization: Bearer $(gcloud auth print-access-token)" -H "x-goog-user-project: kc-okf-poc-261122" "https://agentregistry.googleapis.com/v1/projects/kc-okf-poc-261122/locations/global/skills/private-ga4-context"`` (**not yet run**: check for revisions first) |

Not created by us (already there from kc-okf or Agent Platform): the APIs `aiplatform`, `dataplex`, `bigquery`, `apptopology`, `cloudtrace`, `telemetry`, `logging`; the BigQuery dataset `ga4_sample`; the Knowledge Catalog context set; Google's own registry entries (Workspace Agents, Google MCP servers and skills).

Local only (not in the cloud): Langfuse on the home server; `build/` (generated, git-ignored).

Order at the end of the POC: remove the IAM bindings (they need `$P`, which needs the agent), then delete the agent, then the registry entries, then disable the API.
