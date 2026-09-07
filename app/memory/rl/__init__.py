"""RL memory policy (config F, experimental).

A dependency-light GRPO-inspired trainer that learns the Mem0 resolver's NOOP/UPDATE/ADD
decision on local labelled fixtures. Pure numpy — no torch, no trl, no gym. Produces a
``LinearPolicy`` weights file that ``app.memory.policy.get_policy("rl", ...)`` can load.

Clearly experimental and offline: this is production plumbing for a learned policy, not a
reproduction of any published LLM-scale RL benchmark.
"""

from app.memory.rl.env import LABELS, MemoryDecisionEnv, make_dataset
from app.memory.rl.grpo import GRPOTrainer
from app.memory.rl.train import run

__all__ = ["LABELS", "MemoryDecisionEnv", "make_dataset", "GRPOTrainer", "run"]
