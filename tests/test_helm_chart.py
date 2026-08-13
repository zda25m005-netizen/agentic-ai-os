"""Helm chart validation (container-free).

Can't run `helm lint`/`helm template` in CI without helm, so we validate the
chart's structure, that values.yaml carries the knobs, and that every template
references `.Values` (i.e. is actually parameterized, not hard-coded).
"""
from pathlib import Path

import yaml

CHART = Path(__file__).resolve().parents[1] / "charts" / "agentic"


def test_chart_metadata():
    meta = yaml.safe_load((CHART / "Chart.yaml").read_text())
    assert meta["apiVersion"] == "v2"
    assert meta["name"] == "agentic-ai-os"
    assert meta["version"]


def test_values_expose_key_knobs():
    v = yaml.safe_load((CHART / "values.yaml").read_text())
    assert v["api"]["image"] and v["api"]["replicas"] and v["api"]["port"] == 8000
    assert v["web"]["port"] == 3000
    for name in ("qdrant", "neo4j", "postgres"):
        assert v["datastores"][name]["image"]
        assert v["datastores"][name]["storage"]


def test_templates_exist():
    for f in ("_helpers.tpl", "api.yaml", "web.yaml", "datastores.yaml"):
        assert (CHART / "templates" / f).is_file(), f"missing template {f}"


def test_templates_are_parameterized():
    for f in ("api.yaml", "web.yaml", "datastores.yaml"):
        text = (CHART / "templates" / f).read_text()
        assert "{{ .Values" in text or "{{ $ds" in text, f"{f} is not templated"


def test_api_template_has_deployment_and_service():
    text = (CHART / "templates" / "api.yaml").read_text()
    assert "kind: Deployment" in text and "kind: Service" in text
    assert "/readyz" in text  # readiness probe wired
