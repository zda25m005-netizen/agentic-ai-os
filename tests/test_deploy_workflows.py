"""Validate the deploy workflows + Makefile targets (structure, not execution).

The real kind smoke-deploy runs on GitHub Actions; here we assert the workflow
YAML is well-formed and wires the right steps, so it can't silently rot.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"


def _flatten_run(wf: dict) -> str:
    """All `run:` script text + step names/uses across every job, concatenated."""
    chunks: list[str] = []
    for job in wf.get("jobs", {}).values():
        for step in job.get("steps", []):
            chunks.append(step.get("name", ""))
            chunks.append(step.get("uses", ""))
            chunks.append(step.get("run", ""))
            chunks.append(str(step.get("with", "")))  # tags/registry live here
    return "\n".join(chunks)


def test_kind_smoke_workflow_deploys_and_health_checks():
    wf = yaml.safe_load((WF / "k8s-smoke.yml").read_text())
    assert "kind-smoke" in wf["jobs"]
    text = _flatten_run(wf)
    assert "helm/kind-action" in text          # spins up a cluster
    assert "helm upgrade --install agentic charts/agentic" in text
    assert "kubectl rollout status deploy/agentic-api" in text
    assert "/health" in text                    # smoke test hits the API


def test_release_workflow_builds_both_images_on_tags():
    wf = yaml.safe_load((WF / "release-images.yml").read_text())
    # 'on' can parse as bool True (YAML gotcha); accept either key.
    triggers = wf.get("on") or wf.get(True)
    assert "v*" in str(triggers)
    text = _flatten_run(wf)
    assert "docker/build-push-action" in text
    assert text.count("build-push-action") >= 2  # api + web
    assert "ghcr.io" in text


def test_makefile_has_k8s_targets():
    mk = (ROOT / "Makefile").read_text()
    assert "k8s-up:" in mk and "k8s-down:" in mk
    assert "kind create cluster" in mk and "kind delete cluster" in mk
