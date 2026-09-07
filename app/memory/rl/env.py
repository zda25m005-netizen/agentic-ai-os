"""Memory-decision environment (config F).

A one-step contextual-bandit MDP over the Mem0 resolver's decision:

    state  = feature vector of (candidate vs. its most-similar memory)
    action = NOOP | UPDATE | ADD
    reward = how good that action was, given the state's *labelled* optimal action

The reward is shaped from the memory engine's own quality signals — the same failure
modes the eval harness measures:

    correct action                         -> +1.0
    ADD a duplicate (should be NOOP)       -> -0.5  (irrelevant/duplicate leak)
    keep a stale fact (should be UPDATE)   -> -1.0  (stale leak — the worst error)
    drop a new fact (should be ADD)        -> -1.0  (recall loss)
    any other wrong / illegal action       -> -0.7

States are generated synthetically but faithfully: the three canonical cases (near-
duplicate, explicit correction, novel fact) span the same feature regions the real
resolver sees. Everything is seeded, so training and tests are reproducible.
"""

from __future__ import annotations

import numpy as np

from app.memory.policy import ADD, NOOP, UPDATE, features

# Labelled scenario families -> optimal action.
LABELS = {
    "duplicate": NOOP,
    "correction": UPDATE,
    "novel": ADD,
    "novel_weak_overlap": ADD,
}


def _sample_state(rng: np.random.Generator, kind: str) -> dict:
    """Draw a plausible feature dict for a scenario family."""
    if kind == "duplicate":
        return {
            "best_sim": float(rng.uniform(0.82, 0.99)),
            "is_correction": bool(rng.random() < 0.15),
            "has_best": True,
            "exact_match": bool(rng.random() < 0.3),
        }
    if kind == "correction":
        return {
            "best_sim": float(rng.uniform(0.30, 0.65)),
            "is_correction": True,
            "has_best": True,
            "exact_match": False,
        }
    if kind == "novel":
        return {
            "best_sim": float(rng.uniform(0.0, 0.12)),
            "is_correction": False,
            "has_best": bool(rng.random() < 0.4),
            "exact_match": False,
        }
    # novel but with a weakly-similar neighbor present
    return {
        "best_sim": float(rng.uniform(0.12, 0.28)),
        "is_correction": False,
        "has_best": True,
        "exact_match": False,
    }


def make_dataset(n: int = 400, seed: int = 0) -> list[dict]:
    """Build a labelled dataset of ``{x, feats, optimal}`` decision states."""
    rng = np.random.default_rng(seed)
    kinds = list(LABELS)
    data: list[dict] = []
    for _ in range(n):
        kind = kinds[int(rng.integers(len(kinds)))]
        feats = _sample_state(rng, kind)
        x = np.array(
            features(
                best_sim=feats["best_sim"],
                is_correction=feats["is_correction"],
                has_best=feats["has_best"],
                exact_match=feats["exact_match"],
            )
        )
        data.append({"x": x, "feats": feats, "optimal": LABELS[kind], "kind": kind})
    return data


def reward(state: dict, action: int) -> float:
    """Reward for taking ``action`` in ``state`` (see module docstring)."""
    optimal = state["optimal"]
    has_best = state["feats"]["has_best"]
    # Illegal actions (UPDATE/NOOP without a similar record) are strongly discouraged.
    if action in (NOOP, UPDATE) and not has_best:
        return -1.0
    if action == optimal:
        return 1.0
    if optimal == NOOP and action == ADD:
        return -0.5  # duplicate leak
    if optimal == UPDATE and action == ADD:
        return -1.0  # stale leak
    if optimal == ADD and action == NOOP:
        return -1.0  # recall loss
    return -0.7


class MemoryDecisionEnv:
    """Tiny env wrapper over the labelled dataset (contextual bandit)."""

    def __init__(self, n: int = 400, seed: int = 0):
        self.data = make_dataset(n=n, seed=seed)

    def __len__(self) -> int:
        return len(self.data)

    def states(self) -> list[dict]:
        return self.data

    def reward(self, state: dict, action: int) -> float:
        return reward(state, action)
