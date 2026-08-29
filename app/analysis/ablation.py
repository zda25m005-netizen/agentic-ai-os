"""Ablation study (Phase 15): evidence-first pipeline vs a naive baseline.

The experiment isolates the *evidence layer*. Both arms read the same research
text; the baseline models "LLM -> answer -> report" (statements with no source
linking or verification), while the system arm runs the full evidence-first
pipeline (source linking, cross-source verification, grounded findings). Scored
on the same rubric, the difference quantifies what the evidence layer buys:
citation coverage, claim grounding, verification rate, and fewer unsupported
figures. Deterministic and offline, so the result is reproducible.
"""
from __future__ import annotations

from app.analysis.artifact import ArtifactFinding
from app.analysis.benchmark import BenchmarkItem, load_dataset
from app.analysis.claims import extract_claims
from app.analysis.metrics import score
from app.analysis.pipeline import build_analysis_artifact, parse_objective

_AVG_KEYS = ("citation_coverage", "claim_grounding", "verified_rate",
             "unsupported_figure_rate", "avg_source_reliability")


def _evidence_first(item: BenchmarkItem) -> dict:
    art = build_analysis_artifact(item.mission(), item.tasks())
    return score(art.claims, art.findings, art.sources)


def _baseline(item: BenchmarkItem) -> dict:
    """Naive arm: statements extracted with no source linking or verification."""
    entities, _dims, _mt = parse_objective(item.objective)
    claims = []
    idx = 1
    for _desc, text in item.results:
        cs = extract_claims(text, [], entities, start=idx)   # no source_ids -> ungrounded
        claims.extend(cs)
        idx += len(cs)
    findings = [ArtifactFinding(id=f"F{i}", observation=c.statement, evidence_ids=[c.id])
                for i, c in enumerate(claims, 1)]
    return score(claims, findings, [])


def _mean(rows: list[dict]) -> dict:
    n = len(rows) or 1
    out = {k: round(sum(r[k] for r in rows) / n, 3) for k in _AVG_KEYS}
    out["contradictions_flagged"] = sum(r["contradictions_flagged"] for r in rows)
    return out


def run_ablation(dataset: list[BenchmarkItem] | None = None) -> dict:
    """Run both arms over the benchmark and return aggregated + per-item results."""
    items = dataset or load_dataset()
    sys_rows = [_evidence_first(it) for it in items]
    base_rows = [_baseline(it) for it in items]
    system, baseline = _mean(sys_rows), _mean(base_rows)
    delta = {k: round(system[k] - baseline[k], 3) for k in _AVG_KEYS}
    return {
        "n_items": len(items), "system": system, "baseline": baseline, "delta": delta,
        "per_item": [{"id": it.id, "category": it.category,
                      "system": s, "baseline": b}
                     for it, s, b in zip(items, sys_rows, base_rows, strict=True)],
        "note": "Evaluation metrics for the evidence layer; deterministic ablation.",
    }


def format_ablation(result: dict) -> str:
    """Render the aggregate comparison as a small markdown table."""
    s, b, d = result["system"], result["baseline"], result["delta"]
    lines = [f"Evidence-first ablation over {result['n_items']} benchmark items\n",
             "| Metric | Baseline | Evidence-first | Delta |",
             "| --- | --: | --: | --: |"]
    for k in _AVG_KEYS:
        lines.append(f"| {k.replace('_', ' ')} | {b[k]:.3f} | {s[k]:.3f} | {d[k]:+.3f} |")
    return "\n".join(lines)
