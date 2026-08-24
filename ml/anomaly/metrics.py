"""Ranking + classification metrics for anomaly detection — pure numpy.

Kept dependency-free (no sklearn) so training/eval run in CI. Day 16 builds
threshold selection, calibration, and the registry on top of these.
"""
from __future__ import annotations

import numpy as np


def _rankdata(a: np.ndarray) -> np.ndarray:
    """1-based ranks with ties averaged (like scipy.stats.rankdata)."""
    a = np.asarray(a, dtype=float)
    order = a.argsort(kind="mergesort")
    ranks = np.empty(len(a), dtype=float)
    sa = a[order]
    i, n = 0, len(a)
    while i < n:
        j = i
        while j + 1 < n and sa[j + 1] == sa[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def roc_auc(y: np.ndarray, scores: np.ndarray) -> float:
    """Area under the ROC curve via the Mann-Whitney U statistic (tie-aware)."""
    y = np.asarray(y)
    scores = np.asarray(scores, dtype=float)
    n_pos = int((y == 1).sum())
    n_neg = int((y == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    ranks = _rankdata(scores)
    return float((ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def average_precision(y: np.ndarray, scores: np.ndarray) -> float:
    """PR-AUC (average precision): the anomaly-detection metric that matters most
    under heavy class imbalance."""
    y = np.asarray(y)
    scores = np.asarray(scores, dtype=float)
    total_pos = int((y == 1).sum())
    if total_pos == 0:
        return float("nan")
    order = np.argsort(-scores, kind="mergesort")
    yo = y[order].astype(float)
    tp = np.cumsum(yo)
    fp = np.cumsum(1.0 - yo)
    precision = tp / np.maximum(tp + fp, 1e-12)
    recall = tp / total_pos
    recall_prev = np.concatenate([[0.0], recall[:-1]])
    return float(np.sum((recall - recall_prev) * precision))


def precision_recall_f1(y: np.ndarray, preds: np.ndarray) -> tuple[float, float, float]:
    """Precision, recall, F1 for binary predictions."""
    y = np.asarray(y)
    preds = np.asarray(preds)
    tp = int(((preds == 1) & (y == 1)).sum())
    fp = int(((preds == 1) & (y == 0)).sum())
    fn = int(((preds == 0) & (y == 1)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1
