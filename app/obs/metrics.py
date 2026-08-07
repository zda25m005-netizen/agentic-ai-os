"""Prometheus metrics.

Complements the per-request trace (latency/tokens/cost) with process-wide,
scrapeable counters and histograms: HTTP traffic, LLM token/cost totals, and
per-agent-node / per-tool activity. Exposed at ``/metrics`` for Prometheus.

Kept as thin helper functions so call sites stay one-liners and the metric
objects live in exactly one place (avoids duplicate-registration errors).
"""
from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUESTS = Counter(
    "agentic_requests_total", "HTTP requests", ["endpoint", "method", "status"]
)
REQUEST_LATENCY = Histogram(
    "agentic_request_latency_seconds", "HTTP request latency (s)", ["endpoint"]
)
LLM_TOKENS = Counter("agentic_llm_tokens_total", "LLM tokens used", ["type"])
LLM_COST = Counter("agentic_llm_cost_usd_total", "Estimated LLM cost (USD)")
AGENT_NODE_RUNS = Counter(
    "agentic_agent_node_runs_total", "Agent node executions", ["node"]
)
TOOL_CALLS = Counter("agentic_tool_calls_total", "Tool invocations", ["tool"])


def observe_request(endpoint: str, method: str, status: int, seconds: float) -> None:
    REQUESTS.labels(endpoint=endpoint, method=method, status=str(status)).inc()
    REQUEST_LATENCY.labels(endpoint=endpoint).observe(seconds)


def record_tokens(prompt_tokens: int, completion_tokens: int) -> None:
    if prompt_tokens:
        LLM_TOKENS.labels(type="prompt").inc(prompt_tokens)
    if completion_tokens:
        LLM_TOKENS.labels(type="completion").inc(completion_tokens)


def record_cost(usd: float) -> None:
    if usd:
        LLM_COST.inc(usd)


def inc_agent_node(node: str) -> None:
    AGENT_NODE_RUNS.labels(node=node).inc()


def inc_tool(tool: str) -> None:
    TOOL_CALLS.labels(tool=tool).inc()


def render() -> tuple[bytes, str]:
    """Return (payload, content_type) for the /metrics response."""
    return generate_latest(), CONTENT_TYPE_LATEST
