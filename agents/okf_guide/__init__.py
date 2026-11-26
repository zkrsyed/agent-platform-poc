"""ga4_guide package. Importing it switches on tracing when the OTEL_* settings are present."""

from google.adk.telemetry.setup import maybe_set_otel_providers
from opentelemetry import trace

# `adk web` installs its own exporters at startup; `adk run` and plain scripts don't.
# So only act if nobody has installed a tracer provider yet.
if isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider):
    maybe_set_otel_providers()

from . import agent as agent  # noqa: E402
