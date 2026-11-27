# Cloud resources created by this POC

Every resource created in project `kc-okf-poc-261122` goes here, along with the lesson that made it and the command that removes it. Updated 2026-11-27 after lesson 11. Run the commands from the repo folder; every delete changes the cloud, so ask first.

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
| 11 | Enabled APIs | `networkservices`, `iam`, `iap`, `networksecurity`, `cloudresourcemanager` | free to enable | leave on (other lessons may use them), or `gcloud services disable NAME --project kc-okf-poc-261122` |
| 11 | **Agent Gateway** (Agent-to-Anywhere, Google-managed) | `ga4-egress` (us-central1) | **price not found; logs call it `SECURE_WEB_GATEWAY`, likely billed per hour (guess)**. **Still running** at the end of lesson 11 | lesson 11 README, **Part E** (redeploy the agent without `--gateway` first) |
| 11 | Authz extension (IAP guard), ENFORCED | `ga4-iap-guard` (us-central1) | likely free (config) | `gcloud beta service-extensions authz-extensions delete ga4-iap-guard --location us-central1 --project kc-okf-poc-261122` (Part E) |
| 11 | Authz policy (hookup) | `ga4-egress-authz` (us-central1) | likely free (config) | `gcloud network-security authz-policies delete ga4-egress-authz --location us-central1 --project kc-okf-poc-261122` (Part E) |
| 11 | Access policy + policy binding (the list: platform, BigQuery, catalog) | `ga4-guide-egress` (global) | free (config) | `gcloud iam policy-bindings delete ga4-guide-egress --project kc-okf-poc-261122 --location global`, then `gcloud iam access-policies delete ga4-guide-egress --project kc-okf-poc-261122 --location global` |
| 11 | Agent settings | `ga4-guide` bound to `ga4-egress`, tracing on (`--otel_to_cloud`) | traces and logs: pay per use, tiny | redeploy without `--gateway` (Part E); keep `--otel_to_cloud` |

**Billing (2026-11-27):** $41.51 this month, all Vertex AI (Gemini); budget "kc-okf-poc" $20/month on the billing account (alerts at 50/90/100/150%, **no cap**). Check Billing → Reports (group by service, then SKU) after each lesson.

Not created by us (already there from kc-okf or Agent Platform): the APIs `aiplatform`, `dataplex`, `bigquery`, `apptopology`, `cloudtrace`, `telemetry`, `logging`; the BigQuery dataset `ga4_sample`; the Knowledge Catalog context set; Google's own registry entries (Workspace Agents, Google MCP servers and skills).

Local only (not in the cloud): Langfuse on the home server; `build/` (generated, git-ignored).

Order at the end of the POC: turn the gateway off (lesson 11 Part E) and delete the access policy, then remove the IAM bindings (they need `$P`, which needs the agent), then delete the agent, then the registry entries, then disable the API.
