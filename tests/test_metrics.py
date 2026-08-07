"""Prometheus metrics tests."""
from fastapi.testclient import TestClient

from app.api.main import app
from app.obs import metrics

client = TestClient(app)


def test_helpers_emit_expected_series():
    metrics.inc_tool("calculator")
    metrics.inc_agent_node("planner")
    metrics.record_tokens(10, 5)
    metrics.record_cost(0.001)

    payload, content_type = metrics.render()
    text = payload.decode()
    assert "text/plain" in content_type
    assert 'agentic_tool_calls_total{tool="calculator"}' in text
    assert 'agentic_agent_node_runs_total{node="planner"}' in text
    assert 'agentic_llm_tokens_total{type="prompt"}' in text
    assert "agentic_llm_cost_usd_total" in text


def test_metrics_endpoint_returns_prometheus_text():
    client.get("/health")  # generate at least one request
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]
    body = r.text
    assert "agentic_requests_total" in body
    assert "agentic_request_latency_seconds" in body


def test_request_middleware_counts_by_endpoint():
    client.get("/health")
    body = client.get("/metrics").text
    # the /health path should appear as a labeled counter series
    assert 'endpoint="/health"' in body
