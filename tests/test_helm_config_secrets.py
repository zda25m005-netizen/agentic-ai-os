"""ConfigMap/Secret wiring + no-leaked-secrets checks for the Helm chart."""
import re
from pathlib import Path

import yaml

CHART = Path(__file__).resolve().parents[1] / "charts" / "agentic"
TPL = CHART / "templates"

# Anything that looks like a real credential must never be committed.
_SECRET_LITERALS = re.compile(r"sk-[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{16}")


def test_configmap_is_from_values_config():
    text = (TPL / "configmap.yaml").read_text()
    assert "kind: ConfigMap" in text
    assert ".Values.config" in text  # templated, not hard-coded
    cfg = yaml.safe_load((CHART / "values.yaml").read_text())["config"]
    assert "QDRANT_URL" in cfg and "NEO4J_URI" in cfg and "DATABASE_URL" in cfg


def test_secret_is_opaque_and_templated():
    text = (TPL / "secret.yaml").read_text()
    assert "kind: Secret" in text and "type: Opaque" in text
    assert ".Values.secrets" in text


def test_api_uses_envfrom_not_inline_secrets():
    text = (TPL / "api.yaml").read_text()
    assert "envFrom:" in text
    assert "configMapRef" in text and "secretRef" in text
    # secrets must NOT be inlined as plaintext env in the deployment
    assert "OPENAI_API_KEY" not in text


def test_default_secrets_are_empty():
    v = yaml.safe_load((CHART / "values.yaml").read_text())
    assert v["secrets"]["OPENAI_API_KEY"] == ""
    assert v["secrets"]["JWT_SECRET"] == ""


def test_no_secret_literals_anywhere_in_chart():
    for path in CHART.rglob("*"):
        if path.is_file() and path.suffix in (".yaml", ".yml", ".tpl"):
            assert not _SECRET_LITERALS.search(path.read_text()), f"secret-like literal in {path}"


def test_prod_values_enable_ingress_and_prod_env():
    prod = yaml.safe_load((CHART / "values-prod.yaml").read_text())
    assert prod["ingress"]["enabled"] is True
    assert prod["config"]["APP_ENV"] == "prod"
