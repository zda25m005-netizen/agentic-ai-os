"""Train and compare anomaly models, logging each run to the experiment tracker.

    python -m ml.anomaly.train --n 5000 --seed 42

Fits the feature pipeline on train, standardizes, trains every available model,
scores the validation split, and logs ROC-AUC + PR-AUC per model. On a machine
with scikit-learn/MLflow it compares five models and logs to MLflow; in CI it
compares the three numpy models and logs to a local JSON store.
"""
from __future__ import annotations

import argparse

import numpy as np

from ml.anomaly.data import GeneratorConfig, generate, split
from ml.anomaly.features import FeaturePipeline, to_xy
from ml.anomaly.metrics import average_precision, roc_auc
from ml.anomaly.models import Standardizer, build_models
from ml.anomaly.tracking import Tracker


def train_all(train_rows, val_rows, tracker: Tracker | None = None, seed: int = 0) -> list[dict]:
    """Train every model on `train_rows`, evaluate on `val_rows`. Returns a results table."""
    tracker = tracker or Tracker()
    pipe = FeaturePipeline().fit(train_rows)
    x_tr, y_tr = to_xy(pipe, train_rows)
    x_va, y_va = to_xy(pipe, val_rows)
    x_tr, y_tr = np.asarray(x_tr, dtype=float), np.asarray(y_tr)
    x_va, y_va = np.asarray(x_va, dtype=float), np.asarray(y_va)

    std = Standardizer().fit(x_tr)
    x_tr_s, x_va_s = std.transform(x_tr), std.transform(x_va)

    results: list[dict] = []
    for model in build_models():
        model.fit(x_tr_s, y_tr)
        scores = np.asarray(model.score(x_va_s), dtype=float)
        auc = roc_auc(y_va, scores)
        ap = average_precision(y_va, scores)
        with tracker.run(model.name) as run:
            run.log_params({"model": model.name, "seed": seed, "n_train": int(len(y_tr))})
            run.log_metrics({"roc_auc": auc, "pr_auc": ap})
        results.append({"model": model.name, "roc_auc": auc, "pr_auc": ap})

    results.sort(key=lambda r: r["pr_auc"], reverse=True)
    return results


def main() -> None:
    ap = argparse.ArgumentParser(description="Train + compare anomaly models")
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    cfg = GeneratorConfig(n_transactions=args.n, seed=args.seed)
    rows = generate(cfg)
    s = split(rows, seed=args.seed)
    tracker = Tracker()
    results = train_all(s.train, s.val, tracker=tracker, seed=args.seed)

    print(f"tracking backend: {tracker.backend}")
    print(f"{'model':<20}{'ROC-AUC':>10}{'PR-AUC':>10}")
    for r in results:
        print(f"{r['model']:<20}{r['roc_auc']:>10.4f}{r['pr_auc']:>10.4f}")
    print(f"\nbest by PR-AUC: {results[0]['model']}")


if __name__ == "__main__":
    main()
