"""CLI: assemble the DPO dataset from stored feedback and write JSONL.

Usage:
    python -m app.feedback.dpo_cli --out eval/datasets/dpo_pairs.jsonl

Reads feedback via the configured backend, builds preference pairs, validates
them, prints stats, and exports TRL-format JSONL for offline preference tuning.
"""
from __future__ import annotations

import argparse
import asyncio

from app.db.session import get_sessionmaker
from app.feedback.dpo import build_preference_pairs, dataset_stats, validate_pairs
from app.feedback.dpo_export import export_jsonl
from app.feedback.store import FeedbackStore

DEFAULT_OUT = "eval/datasets/dpo_pairs.jsonl"


async def build_from_store(store: FeedbackStore, out_path: str) -> dict:
    """Pull feedback, build + validate pairs, export, and return stats."""
    items = await store.recent(limit=10_000)
    pairs = build_preference_pairs(items)
    issues = validate_pairs(pairs)
    if issues:
        print("validation issues:")
        for issue in issues:
            print(f"  - {issue}")
    export_jsonl(pairs, out_path)
    return dataset_stats(pairs)


async def _run(out_path: str) -> None:
    store = FeedbackStore(get_sessionmaker())
    stats = await build_from_store(store, out_path)
    print(f"DPO dataset → {out_path}")
    for key, value in stats.items():
        print(f"  {key}: {value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a DPO dataset from feedback.")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output JSONL path.")
    args = parser.parse_args()
    asyncio.run(_run(args.out))


if __name__ == "__main__":
    main()
