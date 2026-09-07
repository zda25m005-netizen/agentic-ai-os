"""Memory-decision policy (config F) — the pluggable brain of the Mem0 resolver.

The lifecycle resolver must decide, for each candidate memory, one of three actions
against the most-similar existing memory:

    NOOP   — near-duplicate, reinforce the existing record (don't duplicate)
    UPDATE — an explicit correction, supersede the existing record
    ADD    — a genuinely new fact, store it

This module makes that decision swappable behind a tiny interface so the *same*
lifecycle code can run a hand-written rule set or a learned policy:

- ``DeterministicPolicy`` reproduces the original threshold logic EXACTLY, so it is the
  safe default and every existing test/behavior is unchanged.
- ``LinearPolicy`` is a dependency-light learned policy (a numpy softmax over a small
  feature vector) whose weights are trained offline by the GRPO trainer and loaded from
  JSON. Inference needs only numpy — no torch, no trl.
- ``get_policy(mode, ...)`` picks the policy from ``MEMORY_POLICY_MODE`` and *always*
  degrades to deterministic when RL weights are missing or unreadable.

Honesty note: the learned policy is a small linear model over the memory-decision MDP,
trained on local labelled fixtures — it is GRPO-*inspired* production plumbing, not a
reproduction of any published LLM-scale benchmark.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

# Action space (index order is fixed — weights depend on it).
NOOP, UPDATE, ADD = 0, 1, 2
ACTIONS = ("NOOP", "UPDATE", "ADD")

# Default resolver thresholds (the historical constants).
DUP_THRESHOLD = 0.8
CORRECTION_THRESHOLD = 0.25


def features(
    *, best_sim: float, is_correction: bool, has_best: bool, exact_match: bool
) -> list[float]:
    """Feature vector for one resolve decision (order is part of the policy contract)."""
    bs = float(best_sim)
    ic = 1.0 if is_correction else 0.0
    hb = 1.0 if has_best else 0.0
    em = 1.0 if exact_match else 0.0
    return [1.0, bs, ic, hb, em, bs * ic]  # bias, sim, correction, has_best, exact, sim×corr


N_FEATURES = 6
N_ACTIONS = 3


class MemoryPolicy:
    """Interface: map a feature dict to one of NOOP / UPDATE / ADD."""

    def decide(self, feats: dict) -> int:  # pragma: no cover - interface
        raise NotImplementedError


class DeterministicPolicy(MemoryPolicy):
    """The original rule set, extracted verbatim so behavior is byte-for-byte the same."""

    def __init__(
        self,
        dup_threshold: float = DUP_THRESHOLD,
        correction_threshold: float = CORRECTION_THRESHOLD,
    ):
        self.dup_threshold = dup_threshold
        self.correction_threshold = correction_threshold

    def decide(self, feats: dict) -> int:
        has_best = bool(feats.get("has_best"))
        best_sim = float(feats.get("best_sim", 0.0))
        if has_best and (feats.get("exact_match") or best_sim >= self.dup_threshold):
            return NOOP
        if has_best and feats.get("is_correction") and best_sim >= self.correction_threshold:
            return UPDATE
        return ADD


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()


class LinearPolicy(MemoryPolicy):
    """A learned softmax policy: ``p(action) = softmax(W · x)`` over the feature vector.

    Small and inference-only-numpy. Trained by ``app.memory.rl``. ``decide`` is greedy
    (argmax) so serving is deterministic once weights are fixed.
    """

    def __init__(self, weights: np.ndarray | None = None):
        if weights is None:
            weights = np.zeros((N_ACTIONS, N_FEATURES), dtype=float)
        self.W = np.asarray(weights, dtype=float)
        if self.W.shape != (N_ACTIONS, N_FEATURES):
            raise ValueError(f"weights must be {N_ACTIONS}x{N_FEATURES}, got {self.W.shape}")

    # --- inference -----------------------------------------------------------
    def probs(self, x: np.ndarray) -> np.ndarray:
        return _softmax(self.W @ x)

    def decide(self, feats: dict) -> int:
        x = np.array(
            features(
                best_sim=feats.get("best_sim", 0.0),
                is_correction=feats.get("is_correction", False),
                has_best=feats.get("has_best", False),
                exact_match=feats.get("exact_match", False),
            )
        )
        # A learned policy can pick an action that's illegal for this state
        # (UPDATE/NOOP with no similar record); clamp those to ADD for safety.
        action = int(np.argmax(self.probs(x)))
        if not feats.get("has_best") and action in (NOOP, UPDATE):
            return ADD
        return action

    # --- persistence ---------------------------------------------------------
    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps({"weights": self.W.tolist(), "actions": list(ACTIONS)}))

    @classmethod
    def load(cls, path: str | Path) -> LinearPolicy:
        data = json.loads(Path(path).read_text())
        return cls(np.array(data["weights"], dtype=float))


def get_policy(
    mode: str = "deterministic",
    *,
    weights_path: str | Path | None = None,
    backend: str = "linear",
    llm_model: str | None = None,
    lora_adapter: str | None = None,
) -> MemoryPolicy:
    """Pick a resolver policy from the mode + backend, always degrading safely.

    - ``mode != "rl"`` (default) → DeterministicPolicy (the safe rule set).
    - ``mode == "rl"`` and ``backend == "llm"`` (config G) → an LLM memory policy, which
      itself falls back to a heuristic when torch/transformers are unavailable.
    - ``mode == "rl"`` and ``backend == "linear"`` (config F) → LinearPolicy from
      ``weights_path`` if present & valid, else deterministic.

    The imports for the LLM backend are done lazily here so importing this module never
    pulls in the ML stack (and avoids an import cycle with the trajectory layer).
    """
    if mode != "rl":
        return DeterministicPolicy()
    if backend == "llm":
        try:
            from app.memory.llm_policy import LLMMemoryPolicy

            return LLMMemoryPolicy(
                llm_model or "Qwen/Qwen2.5-0.5B-Instruct",
                adapter_path=(lora_adapter or None),
            )
        except Exception:
            return DeterministicPolicy()
    if weights_path and Path(weights_path).exists():
        try:
            return LinearPolicy.load(weights_path)
        except Exception:
            return DeterministicPolicy()
    return DeterministicPolicy()
