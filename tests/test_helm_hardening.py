"""Hardening checks: non-root securityContext, graceful shutdown, NetworkPolicies."""
from pathlib import Path

import yaml

CHART = Path(__file__).resolve().parents[1] / "charts" / "agentic"
TPL = CHART / "templates"


def test_security_context_values_are_nonroot():
    v = yaml.safe_load((CHART / "values.yaml").read_text())
    assert v["podSecurityContext"]["runAsNonRoot"] is True
    assert v["podSecurityContext"]["runAsUser"] >= 1000
    assert v["containerSecurityContext"]["allowPrivilegeEscalation"] is False
    assert v["containerSecurityContext"]["capabilities"]["drop"] == ["ALL"]


def test_api_and_web_apply_security_context():
    for f in ("api.yaml", "web.yaml"):
        text = (TPL / f).read_text()
        assert ".Values.podSecurityContext" in text
        assert ".Values.containerSecurityContext" in text


def test_graceful_shutdown_wired():
    for f in ("api.yaml", "web.yaml"):
        text = (TPL / f).read_text()
        assert "terminationGracePeriodSeconds" in text
        assert "preStop" in text  # drain hook


def test_probes_are_tuned():
    text = (TPL / "api.yaml").read_text()
    assert "timeoutSeconds" in text and "failureThreshold" in text


def test_networkpolicy_gated_and_least_privilege():
    text = (TPL / "networkpolicy.yaml").read_text()
    assert text.lstrip().startswith("{{- if .Values.networkPolicy.enabled }}")
    assert "kind: NetworkPolicy" in text
    assert "default-deny-ingress" in text
    assert "allow-web-to-api" in text
    assert "allow-api-to-datastores" in text


def test_prod_enables_networkpolicy():
    v = yaml.safe_load((CHART / "values-prod.yaml").read_text())
    assert v["networkPolicy"]["enabled"] is True
