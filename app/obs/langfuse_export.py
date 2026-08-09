"""Export a request's trace to Langfuse (LLM-native observability).

Prometheus gives aggregate metrics; Langfuse gives per-run, nested traces —
every span (planner, executor, tool, LLM call) with its timing, and LLM calls
recorded as `generation`s with model + token usage. This complements, not
replaces, the Prometheus/Grafana view.

Design: the Langfuse SDK is imported lazily and the client is injectable, so the
app runs (and CI passes) with no Langfuse installed or configured. Export is a
best-effort no-op unless both keys are set; it never breaks a request.
"""
from __future__ import annotations

from app.core.config import get_settings
from app.obs.tracing import Trace

LLM_SPAN = "llm.chat"


def is_enabled() -> bool:
    """True only when both Langfuse keys are configured."""
    s = get_settings()
    return bool(s.langfuse_public_key and s.langfuse_secret_key)


def build_client():
    """Construct a Langfuse client from config, or None if unavailable."""
    if not is_enabled():
        return None
    try:
        from langfuse import Langfuse
    except ImportError:
        return None
    s = get_settings()
    return Langfuse(
        public_key=s.langfuse_public_key,
        secret_key=s.langfuse_secret_key,
        host=s.langfuse_host,
    )


def _trace_metadata(trace: Trace, extra: dict | None = None) -> dict:
    """Roll the run's cost/token/latency summary into trace metadata."""
    summary = trace.summary()
    return {
        **(extra or {}),
        "total_ms": summary["total_ms"],
        "prompt_tokens": summary["prompt_tokens"],
        "completion_tokens": summary["completion_tokens"],
        "est_cost_usd": summary["est_cost_usd"],
        "spans": summary["spans"],
    }


def export_trace(
    trace: Trace,
    name: str = "agent-run",
    metadata: dict | None = None,
    client=None,
) -> bool:
    """Send `trace`'s spans to Langfuse. Returns True if exported, else False."""
    client = client or build_client()
    if client is None:
        return False

    lf_trace = client.trace(name=name, metadata=_trace_metadata(trace, metadata))
    for span in trace.spans:
        if span.name == LLM_SPAN:
            lf_trace.generation(
                name=span.name,
                model=span.metadata.get("model"),
                usage={
                    "input": span.metadata.get("prompt_tokens", 0),
                    "output": span.metadata.get("completion_tokens", 0),
                },
                metadata={"duration_ms": span.duration_ms},
            )
        else:
            lf_trace.span(name=span.name, metadata={"duration_ms": span.duration_ms})
    client.flush()
    return True
