"""Write the access-policy rules (the guard's list) for our agent (lesson 11). Changes nothing in the cloud.

  uv run python scripts/egress_rules.py "$P"                    # the 20 Google platform hosts only
  uv run python scripts/egress_rules.py "$P" bigquery           # + BigQuery
  uv run python scripts/egress_rules.py "$P" bigquery catalog   # + BigQuery + the catalog's MCP server

Prints JSON for `gcloud iam access-policies create/update --details-rules=FILE`.
One rule per group, because a condition's list may hold at most 10 items
(verified: EXCEEDS_MAX_CONDITION_LIST_SIZE with 20).
"""

import json
import sys

GROUPS = {
    # The docs' list ("Deploy an agent with Agent Gateway"): what the agent itself needs.
    "platform part 1": [
        "agentregistry.googleapis.com", "logging.googleapis.com", "logging.mtls.googleapis.com",
        "telemetry.googleapis.com", "telemetry.mtls.googleapis.com", "cloudtrace.googleapis.com",
        "cloudtrace.mtls.googleapis.com", "monitoring.googleapis.com", "monitoring.mtls.googleapis.com",
        "secretmanager.googleapis.com",
    ],
    "platform part 2": [
        "secretmanager.mtls.googleapis.com", "cloudresourcemanager.googleapis.com",
        "cloudresourcemanager.mtls.googleapis.com", "iamcredentials.googleapis.com",
        "iamcredentials.mtls.googleapis.com", "aiplatform.googleapis.com", "aiplatform.mtls.googleapis.com",
        "us-central1-aiplatform.googleapis.com", "us-central1-aiplatform.mtls.googleapis.com",
        "aiplatform.us-central1.rep.googleapis.com",
    ],
    # Our agent's tools. Seen in the gateway log (verified): bigquery.mtls... and dataplex.googleapis.com.
    "bigquery": ["bigquery.googleapis.com", "bigquery.mtls.googleapis.com"],
    "catalog": ["dataplex.googleapis.com", "dataplex.mtls.googleapis.com"],
}


def rule(principal: str, label: str, hosts: list[str]) -> dict:
    return {
        "description": f"Lesson 11: {label}",
        "effect": "ALLOW",
        "principals": [principal],
        "operation": {"permissions": ["iap.googleapis.com/resources.egressViaIAP"]},
        "conditions": {"iap.googleapis.com": {"expression":
            f"(destination.is_registered == false) && (destination.unregistered.host in {json.dumps(hosts)})"}},
    }


if len(sys.argv) < 2 or not sys.argv[1].startswith("principal://"):
    sys.exit('usage: egress_rules.py "principal://..." [bigquery] [catalog]   (is $P empty? run the P= line)')
principal, extras = sys.argv[1], sys.argv[2:]
wanted = ["platform part 1", "platform part 2"] + [e for e in extras if e in GROUPS]
print(json.dumps([rule(principal, g, GROUPS[g]) for g in wanted], indent=2))
