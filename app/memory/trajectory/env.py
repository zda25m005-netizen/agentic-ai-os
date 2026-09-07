"""Trajectory memory environment (config G).

A one-step decision environment defined over *agent trajectory* steps:

    agent step  ->  (observation, memory_state)  ->  policy picks one of six ops  ->  reward

The observation is what the agent just saw; the memory_state summarizes the store the
policy is managing (size vs. budget, whether a similar memory already exists). The reward
is shaped from the memory failure modes an ML reviewer actually cares about — information
loss, staleness, pollution, missed retrieval, and token bloat — with the worst errors
(losing a useful fact, keeping a stale one, failing to retrieve when asked) penalised hardest.

Pure python/numpy and fully seeded, so training and evaluation are reproducible and need
no ML dependencies. The real LLM policy is scored against exactly this environment.
"""

from __future__ import annotations

import numpy as np

from app.memory.trajectory.actions import MemoryOp
from app.memory.trajectory.dataset import make_trajectories

# Reward table: (optimal_op, taken_op) -> reward. Absent pairs fall through to defaults.
_CORRECT = 1.0
_WORST = -1.0  # information loss / stale leak / missed retrieval
_BAD = -0.7  # pollution / meaningfully wrong
_MILD = -0.4  # wrong but low-harm


def step_reward(state: dict, op: MemoryOp | int) -> float:
    """Reward for taking ``op`` at a trajectory decision ``state``."""
    op = MemoryOp(op)
    optimal = MemoryOp(state["optimal"])
    if op == optimal:
        return _CORRECT

    worst = {
        # dropping / ignoring a genuinely useful new fact -> information loss
        (MemoryOp.STORE, MemoryOp.DISCARD),
        (MemoryOp.STORE, MemoryOp.NOOP),
        # leaving a stale fact in place when a correction arrived -> stale leak
        (MemoryOp.UPDATE, MemoryOp.NOOP),
        (MemoryOp.UPDATE, MemoryOp.STORE),
        # failing to pull the memory the agent needs -> missed retrieval
        (MemoryOp.RETRIEVE, MemoryOp.NOOP),
        (MemoryOp.RETRIEVE, MemoryOp.DISCARD),
    }
    bad = {
        # storing noise / a duplicate -> pollution
        (MemoryOp.DISCARD, MemoryOp.STORE),
        (MemoryOp.NOOP, MemoryOp.STORE),
        # not compressing when over budget -> token bloat
        (MemoryOp.SUMMARIZE, MemoryOp.NOOP),
        (MemoryOp.SUMMARIZE, MemoryOp.STORE),
    }
    if (optimal, op) in worst:
        return _WORST
    if (optimal, op) in bad:
        return _BAD
    return _MILD


class TrajectoryMemoryEnv:
    """Environment over labelled agent-trajectory decision steps."""

    def __init__(self, n: int = 300, seed: int = 0):
        self.trajectories = make_trajectories(n=n, seed=seed)
        self._states = [s for traj in self.trajectories for s in traj["steps"]]

    def __len__(self) -> int:
        return len(self._states)

    def states(self) -> list[dict]:
        return self._states

    def reward(self, state: dict, op: MemoryOp | int) -> float:
        return step_reward(state, op)

    def optimal_actions(self) -> list[int]:
        return [int(s["optimal"]) for s in self._states]

    def sample(self, seed: int = 0) -> dict:
        return self._states[int(np.random.default_rng(seed).integers(len(self._states)))]
