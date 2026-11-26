#!/usr/bin/env bash
# Run any `adk` command with the agent's .env loaded first, so traces always go to Langfuse.
#   ./scripts/adk.sh web agents
#   ./scripts/adk.sh run agents/ga4_guide
cd "$(dirname "$0")/.." || exit 1
export CLOUDSDK_ACTIVE_CONFIG_NAME=kc-okf
set -a
source agents/ga4_guide/.env   # OTEL_* lines (and the Google Cloud settings) become real env vars
set +a
exec uv run adk "$@"
