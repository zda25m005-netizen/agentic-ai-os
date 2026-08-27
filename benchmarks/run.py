"""CLI: run the fault-injection benchmark and write results.json.

    python -m benchmarks.run --per-category 25 --seed 42 --out artifacts/benchmark

Writes results.json (metrics + every task result) — the reproducible source of
the numbers shown on the eval dashboard and landing page.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from benchmarks.harness import run_benchmark
from benchmarks.metrics import aggregate


async def _main(per_category: int, seed: int, out: str) -> None:
    results = await run_benchmark(per_category=per_category, seed=seed)
    metrics = aggregate(results)

    outdir = Path(out)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "results.json").write_text(json.dumps(
        {"config": {"per_category": per_category, "seed": seed},
         "metrics": metrics,
         "tasks": [r.as_dict() for r in results]},
        indent=2,
    ))

    print(f"benchmark: {metrics['n_tasks']} tasks (seed {seed})\n")
    for k in ("task_success_rate", "recovery_rate", "tool_selection_accuracy",
              "memory_retrieval_rate", "safety_block_rate", "planning_validity",
              "human_intervention_rate", "avg_latency_s", "avg_cost_usd"):
        print(f"  {k:<26} {metrics[k]}")
    print("\n  success by category:")
    for cat, rate in metrics["success_by_category"].items():
        print(f"    {cat:<18} {rate}")
    print(f"\nwrote {outdir / 'results.json'}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the fault-injection benchmark")
    ap.add_argument("--per-category", type=int, default=25)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=str, default="artifacts/benchmark")
    args = ap.parse_args()
    asyncio.run(_main(args.per_category, args.seed, args.out))


if __name__ == "__main__":
    main()
