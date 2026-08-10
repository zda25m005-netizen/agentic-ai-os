"""Config smoke tests for the Prometheus + Grafana stack.

Parses the compose file and provisioning configs to assert the wiring is
correct (api is scraped on /metrics, Grafana points at Prometheus) — a
container-free check that the observability stack is coherent.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str) -> dict:
    return yaml.safe_load((ROOT / rel).read_text())


def test_prometheus_scrapes_api_metrics():
    cfg = _load("ops/prometheus/prometheus.yml")
    jobs = {j["job_name"]: j for j in cfg["scrape_configs"]}
    api = jobs["agentic-api"]
    assert api["metrics_path"] == "/metrics"
    assert "api:8000" in api["static_configs"][0]["targets"]


def test_grafana_datasource_points_at_prometheus():
    cfg = _load("ops/grafana/provisioning/datasources/datasource.yml")
    ds = cfg["datasources"][0]
    assert ds["type"] == "prometheus"
    assert ds["url"] == "http://prometheus:9090"
    assert ds["isDefault"] is True


def test_compose_defines_prometheus_and_grafana():
    compose = _load("docker-compose.yml")
    services = compose["services"]
    assert "prometheus" in services and "grafana" in services
    # Prometheus mounts our config directory (scrape config + alert rules)
    mounts = " ".join(services["prometheus"].get("volumes", []))
    assert "/etc/prometheus" in mounts
    # Grafana provisioning is mounted
    gmounts = " ".join(services["grafana"].get("volumes", []))
    assert "provisioning" in gmounts
