"""Train + persist the RL memory policy (config F, experimental).

    python -m app.memory.rl.train                 # writes memory_policy.json
    python -m app.memory.rl.train --out w.json --epochs 60

Trains the GRPO policy on the local labelled fixtures, saves the weights where
``get_policy("rl", weights_path=...)`` can load them, and prints a JSON report. No
external RL frameworks; runs in well under a second.
"""

from __future__ import annotations

import argparse
import json

from app.core.config import get_settings
from app.memory.rl.env import MemoryDecisionEnv
from app.memory.rl.grpo import GRPOTrainer


def run(
    out_path: str | None = None,
    *,
    epochs: int = 40,
    n: int = 400,
    group_size: int = 8,
    lr: float = 0.3,
    seed: int = 0,
) -> dict:
    """Train, save weights, and return a reproducible report."""
    out_path = out_path or get_settings().memory_policy_weights
    env = MemoryDecisionEnv(n=n, seed=seed)
    trainer = GRPOTrainer(group_size=group_size, lr=lr, seed=seed)
    report = trainer.train(env, epochs=epochs)
    trainer.policy().save(out_path)
    report["weights_path"] = out_path
    report["dataset_size"] = len(env)
    # keep the report compact — drop the per-epoch curve from the returned summary
    report.pop("history", None)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="Train the RL memory policy (config F).")
    ap.add_argument("--out", default=None, help="weights output path (default: config)")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--group-size", type=int, default=8)
    ap.add_argument("--lr", type=float, default=0.3)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    report = run(
        args.out,
        epochs=args.epochs,
        n=args.n,
        group_size=args.group_size,
        lr=args.lr,
        seed=args.seed,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
