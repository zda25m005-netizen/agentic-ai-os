"""Ingress + HPA template validation for the Helm chart (container-free)."""
from pathlib import Path

import yaml

CHART = Path(__file__).resolve().parents[1] / "charts" / "agentic"
TPL = CHART / "templates"


def test_ingress_is_gated_and_routes_both_services():
    text = (TPL / "ingress.yaml").read_text()
    assert text.lstrip().startswith("{{- if .Values.ingress.enabled }}")
    assert text.rstrip().endswith("{{- end }}")     # disabled -> renders empty
    assert "networking.k8s.io/v1" in text
    assert "kind: Ingress" in text
    # both backends, by service name + templated port
    assert "name: api" in text and "{{ .Values.api.port }}" in text
    assert "name: web" in text and "{{ .Values.web.port }}" in text
    assert "{{ .Values.ingress.host" in text


def test_hpa_is_gated_and_targets_the_api_deployment():
    text = (TPL / "hpa.yaml").read_text()
    assert text.lstrip().startswith("{{- if .Values.autoscaling.enabled }}")
    assert "autoscaling/v2" in text
    assert "kind: HorizontalPodAutoscaler" in text
    assert "name: agentic-api" in text  # scaleTargetRef
    assert "averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}" in text


def test_default_values_disable_ingress_and_hpa():
    v = yaml.safe_load((CHART / "values.yaml").read_text())
    assert v["ingress"]["enabled"] is False
    assert v["autoscaling"]["enabled"] is False
    assert v["autoscaling"]["maxReplicas"] >= v["autoscaling"]["minReplicas"]


def test_prod_values_enable_ingress_and_hpa():
    v = yaml.safe_load((CHART / "values-prod.yaml").read_text())
    assert v["ingress"]["enabled"] is True
    assert v["autoscaling"]["enabled"] is True
    assert v["autoscaling"]["maxReplicas"] == 10
