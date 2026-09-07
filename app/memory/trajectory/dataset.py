"""Labelled agent trajectories for the trajectory memory environment (config G).

Each trajectory is a short sequence of decision steps. Every step carries:

    observation   — the text the agent just produced/observed
    memory_state  — a compact summary of the store at that moment
    feats         — scalar features (similarity to nearest memory, correction cue, etc.)
    optimal       — the gold MemoryOp for that step (the label used for reward + accuracy)
    kind          — which situation the step exemplifies (for stratified reporting)

The situations span the six ops so a policy is exercised on all of them:
novel fact -> STORE, correction -> UPDATE, duplicate -> NOOP, noise -> DISCARD,
user question -> RETRIEVE, over-budget store -> SUMMARIZE.

Synthetic but faithful: features occupy the same regions the real resolver sees. Seeded.
"""

from __future__ import annotations

import numpy as np

from app.memory.trajectory.actions import MemoryOp

# Situation family -> (optimal op, feature sampler). Features are plausible scalar signals
# the policy/env can read; the LLM policy instead reads the text fields.
_SITUATIONS = ("novel", "correction", "duplicate", "noise", "question", "over_budget")

_OBS = {
    "novel": "The user is applying for a funded PhD in Germany starting next fall.",
    "correction": "Actually the user switched target country from Switzerland to Germany.",
    "duplicate": "The user is applying for a funded PhD in Germany.",
    "noise": "The weather today is cloudy with a chance of rain.",
    "question": "Which countries is the user targeting for a PhD?",
    "over_budget": "The user also mentioned a preference for machine-learning groups.",
}
_OPTIMAL = {
    "novel": MemoryOp.STORE,
    "correction": MemoryOp.UPDATE,
    "duplicate": MemoryOp.NOOP,
    "noise": MemoryOp.DISCARD,
    "question": MemoryOp.RETRIEVE,
    "over_budget": MemoryOp.SUMMARIZE,
}


def _feats(rng: np.random.Generator, kind: str) -> dict:
    if kind == "novel":
        return {
            "sim": float(rng.uniform(0.0, 0.15)),
            "is_correction": False,
            "is_noise": False,
            "is_query": False,
            "over_budget": False,
        }
    if kind == "correction":
        return {
            "sim": float(rng.uniform(0.3, 0.6)),
            "is_correction": True,
            "is_noise": False,
            "is_query": False,
            "over_budget": False,
        }
    if kind == "duplicate":
        return {
            "sim": float(rng.uniform(0.85, 0.99)),
            "is_correction": False,
            "is_noise": False,
            "is_query": False,
            "over_budget": False,
        }
    if kind == "noise":
        return {
            "sim": float(rng.uniform(0.0, 0.1)),
            "is_correction": False,
            "is_noise": True,
            "is_query": False,
            "over_budget": False,
        }
    if kind == "question":
        return {
            "sim": float(rng.uniform(0.2, 0.5)),
            "is_correction": False,
            "is_noise": False,
            "is_query": True,
            "over_budget": False,
        }
    # over_budget: a storable fact, but the store is already over its token budget
    return {
        "sim": float(rng.uniform(0.1, 0.3)),
        "is_correction": False,
        "is_noise": False,
        "is_query": False,
        "over_budget": True,
    }


def _feature_vector(feats: dict) -> np.ndarray:
    """A fixed-order scalar vector for the heuristic/linear baselines (not the LLM)."""
    return np.array(
        [
            1.0,
            float(feats["sim"]),
            1.0 if feats["is_correction"] else 0.0,
            1.0 if feats["is_noise"] else 0.0,
            1.0 if feats["is_query"] else 0.0,
            1.0 if feats["over_budget"] else 0.0,
        ]
    )


def make_trajectories(n: int = 300, seed: int = 0) -> list[dict]:
    """Build ``n`` short labelled trajectories (each a handful of decision steps)."""
    rng = np.random.default_rng(seed)
    trajectories: list[dict] = []
    for t in range(n):
        n_steps = int(rng.integers(3, 6))
        steps = []
        size = int(rng.integers(0, 12))
        budget = 10
        for _ in range(n_steps):
            kind = _SITUATIONS[int(rng.integers(len(_SITUATIONS)))]
            feats = _feats(rng, kind)
            over = feats["over_budget"] or size > budget
            feats["over_budget"] = over
            optimal = (
                MemoryOp.SUMMARIZE
                if (over and kind not in ("question", "correction"))
                else _OPTIMAL[kind]
            )
            steps.append(
                {
                    "observation": _OBS[kind],
                    "memory_state": {
                        "size": size,
                        "budget": budget,
                        "has_similar": feats["sim"] > 0.3,
                    },
                    "feats": feats,
                    "x": _feature_vector(feats),
                    "optimal": int(optimal),
                    "kind": kind,
                }
            )
            # storing grows the store; summarize shrinks it
            if optimal == MemoryOp.STORE:
                size += 1
            elif optimal == MemoryOp.SUMMARIZE:
                size = max(0, size - 3)
        trajectories.append({"id": f"traj-{t}", "steps": steps})
    return trajectories
