"""Build the SFT dataset: assemble -> split -> write chat-format JSONL.

Usage:
    python -m app.finetune.build_dataset --out data/finetune

Writes train.jsonl and val.jsonl (one chat-format row per line) plus a small
stats print. These files feed the LoRA training run (Colab/Kaggle, Day 19).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.finetune.dataset import build_examples
from app.finetune.format import to_chat, train_val_split

DEFAULT_OUT = "data/finetune"


def write_jsonl(rows: list[dict], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the SFT dataset.")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output directory.")
    parser.add_argument("--val-frac", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    examples = build_examples()
    train, val = train_val_split(examples, val_frac=args.val_frac, seed=args.seed)
    out = Path(args.out)
    n_train = write_jsonl([to_chat(e) for e in train], out / "train.jsonl")
    n_val = write_jsonl([to_chat(e) for e in val], out / "val.jsonl")

    by_source: dict[str, int] = {}
    for e in examples:
        by_source[e.source] = by_source.get(e.source, 0) + 1
    print(f"SFT dataset -> {out}")
    print(f"  total: {len(examples)}  train: {n_train}  val: {n_val}")
    print(f"  by source: {by_source}")


if __name__ == "__main__":
    main()
