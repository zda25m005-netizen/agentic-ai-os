"""Ablation runner (Phase 13). Runs the configs that exist today; the rest are
declared PLANNED so results are never fabricated for unbuilt components.

    A  no_memory                     — baseline (implemented)
    B  existing (episodic+Qdrant)    — requires a live Qdrant/embeddings (skipped offline)
    C  orchestrator                  — canonical engine, this milestone (implemented)
    D  C + Mem0 lifecycle extraction — implemented (extract -> retrieve-similar -> resolve)
    E  D + graph memory              — PLANNED
    F  E + RL memory policy          — PLANNED
"""

from __future__ import annotations

from app.memory.eval.harness import evaluate

STATUS = {
    "A_no_memory": "implemented",
    "B_existing_qdrant": "requires_qdrant",
    "C_orchestrator": "implemented",
    "D_lifecycle": "implemented",
    "E_graph": "planned",
    "F_rl_policy": "planned",
}


def run() -> dict:
    results = {
        "A_no_memory": evaluate("no_memory"),
        "C_orchestrator": evaluate("orchestrator"),
        "D_lifecycle": evaluate("lifecycle"),
    }
    return {
        "status": STATUS,
        "results": results,
        "note": "B/E/F are not executed here; B needs a live Qdrant, E/F are unbuilt. "
        "No numbers are reported for configs that were not actually run.",
    }
