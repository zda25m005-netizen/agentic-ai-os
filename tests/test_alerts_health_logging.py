"""Tests for alert rules, dependency readiness, and structured logging."""
import json
import logging
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from app.api.main import app
from app.obs import health, logging_setup

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


# --- alert rules ---

def test_alert_rules_are_valid_and_wired():
    alerts = yaml.safe_load((ROOT / "ops/prometheus/alerts.yml").read_text())
    rules = alerts["groups"][0]["rules"]
    names = {r["alert"] for r in rules}
    assert {"HighErrorRate", "HighRequestLatencyP95", "LLMCostSpike"} <= names
    assert all(r.get("expr") for r in rules)

    prom = yaml.safe_load((ROOT / "ops/prometheus/prometheus.yml").read_text())
    assert "/etc/prometheus/alerts.yml" in prom["rule_files"]


# --- readiness / dependency health ---

async def test_check_all_ok_when_all_up(monkeypatch):
    async def up():
        return "up"

    monkeypatch.setattr(health, "check_qdrant", up)
    monkeypatch.setattr(health, "check_neo4j", up)
    monkeypatch.setattr(health, "check_postgres", up)
    result = await health.check_all()
    assert result == {"status": "ok",
                      "deps": {"qdrant": "up", "neo4j": "up", "postgres": "up"}}


async def test_check_all_degraded_when_one_down(monkeypatch):
    async def up():
        return "up"

    async def down():
        return "down"

    monkeypatch.setattr(health, "check_qdrant", up)
    monkeypatch.setattr(health, "check_neo4j", down)
    monkeypatch.setattr(health, "check_postgres", up)
    result = await health.check_all()
    assert result["status"] == "degraded"
    assert result["deps"]["neo4j"] == "down"


def test_readyz_endpoint(monkeypatch):
    async def fake_all():
        return {"status": "degraded", "deps": {"qdrant": "up", "neo4j": "down",
                                               "postgres": "up"}}

    monkeypatch.setattr("app.api.main.health.check_all", fake_all)
    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json()["status"] == "degraded"


# --- structured logging ---

def test_json_formatter_emits_request_id_and_extras():
    logging_setup.set_request_id("abc123")
    record = logging.LogRecord("t", logging.INFO, "f", 1, "request", None, None)
    record.method = "GET"
    record.path = "/health"
    record.status = 200
    line = logging_setup.JsonFormatter().format(record)
    data = json.loads(line)
    assert data["request_id"] == "abc123"
    assert data["method"] == "GET" and data["status"] == 200
    assert data["level"] == "INFO"


def test_request_gets_correlation_id_header():
    r = client.get("/health")
    assert r.status_code == 200
    assert len(r.headers.get("X-Request-ID", "")) == 12
