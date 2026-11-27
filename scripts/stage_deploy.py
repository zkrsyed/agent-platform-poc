"""Build a clean, self-contained copy of ga4_guide to deploy (lesson 8). Changes nothing in the cloud.

  uv run python scripts/stage_deploy.py                 # lessons 8-10
  uv run python scripts/stage_deploy.py --gateway       # lesson 11: send the agent's calls through ga4-egress

It creates build/ga4_guide/ with:
  *.py                           copied from agents/ga4_guide (agent.py, __init__.py, guardrails.py)
  skills/ga4-context/            the skill, copied INSIDE the agent folder (only this folder is uploaded)
  .env                           ONLY the Google Cloud settings: no Langfuse key, no OTEL lines
  requirements.txt               the packages the cloud image must install (ADK with MCP and BigQuery)
  .agent_engine_config.json      deploy settings: agent identity, scale to zero
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "agents" / "ga4_guide"
OUT = ROOT / "build" / "ga4_guide"
GATEWAY = "projects/kc-okf-poc-261122/locations/us-central1/agentGateways/ga4-egress"
USE_GATEWAY = "--gateway" in sys.argv[1:]

shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir(parents=True)
for source in SRC.glob("*.py"):  # agent.py, __init__.py, guardrails.py (lesson 9), ...
    shutil.copy2(source, OUT / source.name)
shutil.copytree(ROOT / "skills" / "ga4-context", OUT / "skills" / "ga4-context")

# adk deploy uploads EVERY value in the agent folder's .env as an environment variable,
# so we write a new one with only what the deployed agent needs.
env = (
    "GOOGLE_GENAI_USE_ENTERPRISE=TRUE\n"
    "GOOGLE_CLOUD_PROJECT=kc-okf-poc-261122\n"
    "GOOGLE_CLOUD_LOCATION=us-central1\n"
)
if USE_GATEWAY:
    # Lesson 11: the gateway sits in the middle, so the agent's token can't be tied to its own certificate.
    # The docs turn that off (GOOGLE_API_PREVENT_AGENT_TOKEN_SHARING_FOR_GCP_SERVICES=False; google-auth's newer
    # name is GOOGLE_API_ENABLE_RUNTIME_BOUND_TOKEN). Then the plain catalog host should work (guess, to verify).
    env += "GOOGLE_API_ENABLE_RUNTIME_BOUND_TOKEN=false\n"
    env += "CATALOG_MCP_URL=https://dataplex.googleapis.com/mcp\n"
else:
    # Lesson 9: in Agent Runtime the agent's token is accepted only on the mTLS host (the plain one gave 401).
    env += "CATALOG_MCP_URL=https://dataplex.mtls.googleapis.com/mcp\n"
(OUT / ".env").write_text(env)

# Without this file the cloud image gets only google-adk[a2a], which has no `mcp` package, and the
# container fails to start: "cannot import name 'McpToolset'" (lesson 8, first deploy). `gcp` brings BigQuery.
(OUT / "requirements.txt").write_text("google-adk[a2a,agent-identity,mcp,gcp]==2.15.0\n")

config = {
    "identity_type": "AGENT_IDENTITY",  # the agent gets its own identity (a principal), not a shared service account
    "min_instances": 0,                 # scale to zero when idle (default is 1)
    "max_instances": 1,                 # a POC needs one
}
if USE_GATEWAY:
    # adk deploy passes this file's keys to the SDK's runtimes.update(config=...) (verified in cli_deploy.py)
    config["agent_gateway_config"] = {"agent_to_anywhere_config": {"agent_gateway": GATEWAY}}
(OUT / ".agent_engine_config.json").write_text(json.dumps(config, indent=2) + "\n")

for f in sorted(OUT.rglob("*")):
    if f.is_file():
        print(f.relative_to(ROOT), f.stat().st_size, "bytes")
