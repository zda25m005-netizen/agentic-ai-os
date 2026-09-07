"""Trajectory-level memory control (config G).

Turns an agent trajectory into a sequence of memory-management decisions over a richer
six-action space (STORE / RETRIEVE / UPDATE / SUMMARIZE / DISCARD / NOOP), and provides
the environment + dataset + prompt plumbing an LLM memory policy is trained and evaluated
against. All of this layer is pure-python/numpy and importable with no ML dependencies;
the heavy LLM + LoRA/QLoRA training lives behind lazy imports elsewhere.
"""

from app.memory.trajectory.actions import (
    OPS,
    MemoryOp,
    op_to_resolver_action,
    parse_op,
)
from app.memory.trajectory.dataset import make_trajectories
from app.memory.trajectory.env import TrajectoryMemoryEnv, step_reward
from app.memory.trajectory.prompt import build_prompt, parse_action

__all__ = [
    "OPS",
    "MemoryOp",
    "op_to_resolver_action",
    "parse_op",
    "make_trajectories",
    "TrajectoryMemoryEnv",
    "step_reward",
    "build_prompt",
    "parse_action",
]
