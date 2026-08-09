"""Smoke tests for the Grafana dashboards + provisioning (container-free).

Validates each dashboard JSON is well-formed with panels that carry PromQL
targets, and that the provider config + compose mount + datasource uid line up
so Grafana auto-loads them.
"""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DASH_DIR = ROOT / "ops/grafana/dashboards"
DASHBOARDS = ["agentic-latency.json", "agentic-cost.json", "agentic-agents.json"]


def test_every_dashboard_is_valid_and_has_targets():
    for name in DASHBOARDS:
        data = json.loads((DASH_DIR / name).read_text())
        assert data["title"] and data["uid"]
        assert data["panels"], f"{name} has no panels"
        for panel in data["panels"]:
            assert panel.get("title")
            # every panel queries Prometheus with an expr
            targets = panel.get("targets", [])
            assert targets, f"{name}: panel '{panel['title']}' has no targets"
            assert all(t.get("expr") for t in targets)


def test_dashboards_reference_the_provisioned_datasource_uid():
    ds = yaml.safe_load(
        (ROOT / "ops/grafana/provisioning/datasources/datasource.yml").read_text()
    )
    uid = ds["datasources"][0]["uid"]
    assert uid == "prometheus"
    # at least one panel target uses that uid
    data = json.loads((DASH_DIR / "agentic-latency.json").read_text())
    uids = {
        p.get("datasource", {}).get("uid")
        for p in data["panels"]
    }
    assert uid in uids


def test_provider_points_at_the_mounted_dashboards_path():
    prov = yaml.safe_load(
        (ROOT / "ops/grafana/provisioning/dashboards/provider.yml").read_text()
    )
    path = prov["providers"][0]["options"]["path"]
    assert path == "/var/lib/grafana/dashboards"


def test_compose_mounts_dashboards_folder():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    mounts = " ".join(compose["services"]["grafana"].get("volumes", []))
    assert "/var/lib/grafana/dashboards" in mounts
