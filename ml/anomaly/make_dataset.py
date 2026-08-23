"""CLI: generate the synthetic anomaly dataset, split it, and write a dataset card.

    python -m ml.anomaly.make_dataset --n 5000 --seed 42 --out artifacts/anomaly

Writes train/val/test as JSONL plus card.json and card.md. Output lives under
artifacts/ (gitignored) — reproducible from the seed, so it never needs committing.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ml.anomaly.data import (
    GeneratorConfig,
    Splits,
    dataset_card,
    generate,
    split,
)


def _write_jsonl(path: Path, rows) -> None:
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r.as_dict()) + "\n")


def _card_markdown(card: dict) -> str:
    lines = [
        "# Anomaly Dataset Card",
        "",
        f"- Transactions: **{card['n_transactions']}** across {card['n_users']} users",
        f"- Seed: `{card['seed']}` (fully reproducible)",
        f"- Anomaly rate: target {card['anomaly_rate_target']}, "
        f"actual **{card['anomaly_rate_actual']}** ({card['n_anomalies']} anomalies)",
        "",
        "## Anomaly types",
        "",
    ]
    for name, count in card["anomaly_type_counts"].items():
        lines.append(f"- `{name}`: {count}")
    lines += ["", "## Features", "", ", ".join(f"`{f}`" for f in card["feature_fields"]), ""]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate the anomaly dataset")
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--users", type=int, default=200)
    ap.add_argument("--anomaly-rate", type=float, default=0.06)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=str, default="artifacts/anomaly")
    args = ap.parse_args()

    cfg = GeneratorConfig(
        n_transactions=args.n, n_users=args.users,
        anomaly_rate=args.anomaly_rate, seed=args.seed,
    )
    rows = generate(cfg)
    splits: Splits = split(rows, seed=args.seed)
    card = dataset_card(rows, cfg)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    _write_jsonl(out / "train.jsonl", splits.train)
    _write_jsonl(out / "val.jsonl", splits.val)
    _write_jsonl(out / "test.jsonl", splits.test)
    (out / "card.json").write_text(json.dumps(card, indent=2))
    (out / "card.md").write_text(_card_markdown(card))

    print(f"wrote {len(rows)} transactions to {out}/")
    print(f"  train={len(splits.train)} val={len(splits.val)} test={len(splits.test)}")
    print(f"  anomaly rate={card['anomaly_rate_actual']} types={card['anomaly_type_counts']}")


if __name__ == "__main__":
    main()
