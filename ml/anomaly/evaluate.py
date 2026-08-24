"""Evaluation + model selection: honest test-set metrics and a promoted winner.

Methodology that avoids peeking: models are trained on **train**, the operating
**threshold is chosen on validation** (best-F1), and every reported number is
computed on the held-out **test** split. The winner is picked by validation
PR-AUC, then its test metrics are reported and it's saved to the registry with
its threshold — so serving (Day 17) loads a fully specified, versioned model.
"""
from __future__ import annotations

import argparse

import numpy as np

from ml.anomaly.data import GeneratorConfig, generate, split
from ml.anomaly.metrics import average_precision, precision_recall_f1, roc_auc
from ml.anomaly.registry import save_model
from ml.anomaly.train import features_of, fit_all


def best_f1_threshold(y, scores, n_grid: int = 200) -> tuple[float, float]:
    """Threshold that maximizes F1, swept over a grid of score values."""
    y = np.asarray(y)
    s = np.asarray(scores, dtype=float)
    lo, hi = float(s.min()), float(s.max())
    if hi <= lo:
        return hi, 0.0
    best_thr, best_f1 = lo, -1.0
    for thr in np.linspace(lo, hi, n_grid):
        _, _, f1 = precision_recall_f1(y, (s >= thr).astype(int))
        if f1 > best_f1:
            best_f1, best_thr = f1, float(thr)
    return best_thr, best_f1


def threshold_at_recall(y, scores, target_recall: float = 0.9) -> float:
    """Highest threshold (best precision) that still achieves the target recall."""
    y = np.asarray(y)
    s = np.asarray(scores, dtype=float)
    for thr in np.unique(s)[::-1]:  # descending: recall grows as thr drops
        _, recall, _ = precision_recall_f1(y, (s >= thr).astype(int))
        if recall >= target_recall:
            return float(thr)
    return float(s.min())


def brier_score(y, probs) -> float | None:
    """Calibration for probabilistic scores in [0,1]; None if scores aren't probs."""
    p = np.asarray(probs, dtype=float)
    if p.min() < 0.0 or p.max() > 1.0:
        return None
    return float(np.mean((p - np.asarray(y, dtype=float)) ** 2))


def evaluate_all(train_rows, val_rows, test_rows, seed: int = 0):
    """Train, pick per-model thresholds on val, report metrics on test.

    Returns (pipeline, standardizer, models, results_table, winner_name).
    """
    pipe, std, models = fit_all(train_rows, seed)
    x_va, y_va = features_of(pipe, std, val_rows)
    x_te, y_te = features_of(pipe, std, test_rows)

    results: list[dict] = []
    val_pr: dict[str, float] = {}
    for m in models:
        s_va = np.asarray(m.score(x_va), dtype=float)
        s_te = np.asarray(m.score(x_te), dtype=float)
        thr, _ = best_f1_threshold(y_va, s_va)          # threshold from VAL only
        val_pr[m.name] = average_precision(y_va, s_va)  # selection metric on VAL
        precision, recall, f1 = precision_recall_f1(y_te, (s_te >= thr).astype(int))
        results.append({
            "model": m.name,
            "roc_auc": roc_auc(y_te, s_te),
            "pr_auc": average_precision(y_te, s_te),
            "threshold": thr,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "brier": brier_score(y_te, s_te),
        })

    winner = max(val_pr, key=val_pr.get)  # selected by VAL PR-AUC, reported on TEST
    results.sort(key=lambda r: r["pr_auc"], reverse=True)
    return pipe, std, models, results, winner


def _print_table(results: list[dict], winner: str) -> None:
    hdr = f"{'model':<20}{'ROC-AUC':>9}{'PR-AUC':>9}{'prec':>8}{'recall':>8}{'F1':>8}{'brier':>9}"
    print(hdr)
    for r in results:
        brier = "  n/a" if r["brier"] is None else f"{r['brier']:.4f}"
        star = "  *" if r["model"] == winner else ""
        print(f"{r['model']:<20}{r['roc_auc']:>9.4f}{r['pr_auc']:>9.4f}"
              f"{r['precision']:>8.3f}{r['recall']:>8.3f}{r['f1']:>8.3f}{brier:>9}{star}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluate + promote the winning model")
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rows = generate(GeneratorConfig(n_transactions=args.n, seed=args.seed))
    s = split(rows, seed=args.seed)
    pipe, std, models, results, winner = evaluate_all(s.train, s.val, s.test, seed=args.seed)

    print(f"held-out test metrics (threshold chosen on validation); winner = {winner}\n")
    _print_table(results, winner)

    won = next(m for m in models if m.name == winner)
    won_row = next(r for r in results if r["model"] == winner)
    version = save_model(
        artifact={"model": won, "pipeline": pipe, "standardizer": std,
                  "threshold": won_row["threshold"]},
        metrics={k: won_row[k] for k in ("roc_auc", "pr_auc", "precision", "recall", "f1")},
        meta={"model": winner, "seed": args.seed, "selected_by": "val_pr_auc"},
    )
    print(f"\npromoted {winner} to registry as v{version}")


if __name__ == "__main__":
    main()
