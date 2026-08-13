"""Structural validation of the Kubernetes manifests (container-free).

Parses every k8s/*.yaml doc and asserts the core fields kubeconform would check
(apiVersion, kind, metadata.name, spec), plus the wiring this app needs: api on
8000, web on 3000, and StatefulSets with PVCs for the three datastores.
"""
from pathlib import Path

import yaml

K8S = Path(__file__).resolve().parents[1] / "k8s"


def _load_all() -> list[dict]:
    docs: list[dict] = []
    for path in sorted(K8S.glob("*.yaml")):
        docs.extend(d for d in yaml.safe_load_all(path.read_text()) if d)
    return docs


def test_every_doc_has_core_fields():
    docs = _load_all()
    assert docs, "no manifests found"
    for d in docs:
        assert d.get("apiVersion")
        assert d.get("kind")
        assert d.get("metadata", {}).get("name")
        assert "spec" in d


def _by_kind_name(docs, kind, name):
    return next(
        d for d in docs
        if d["kind"] == kind and d["metadata"]["name"] == name
    )


def test_api_deployment_and_service():
    docs = _load_all()
    dep = _by_kind_name(docs, "Deployment", "agentic-api")
    container = dep["spec"]["template"]["spec"]["containers"][0]
    assert container["ports"][0]["containerPort"] == 8000
    assert container["readinessProbe"]["httpGet"]["path"] == "/readyz"
    svc = _by_kind_name(docs, "Service", "api")
    assert svc["spec"]["ports"][0]["port"] == 8000


def test_web_deployment_targets_3000():
    docs = _load_all()
    dep = _by_kind_name(docs, "Deployment", "agentic-web")
    container = dep["spec"]["template"]["spec"]["containers"][0]
    assert container["ports"][0]["containerPort"] == 3000


def test_datastores_are_statefulsets_with_pvcs():
    docs = _load_all()
    for name in ("qdrant", "neo4j", "postgres"):
        sts = _by_kind_name(docs, "StatefulSet", name)
        assert sts["spec"]["serviceName"] == name
        assert sts["spec"]["volumeClaimTemplates"], f"{name} has no PVC"
        # headless service exists for stable DNS
        svc = _by_kind_name(docs, "Service", name)
        assert svc["spec"]["clusterIP"] == "None"
