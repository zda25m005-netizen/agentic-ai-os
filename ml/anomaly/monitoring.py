"""Production monitoring for the served model: input drift + score distribution.

A model in production silently rots when the live data drifts from what it was
trained on. This module computes two standard drift signals — **PSI** (Population
Stability Index) and the **KS statistic** — between a reference distribution
(captured at training time) and a live batch, plus summary stats of the score
distribution. Pure numpy, so it runs anywhere and feeds the Prometheus panels.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_EPS = 1e-6


def psi(expected, actual, bins: int = 10) -> float:
    """Population Stability Index over quantile bins of `expected`.

    Rule of thumb: <0.1 no shift, 0.1-0.25 moderate, >0.25 significant drift.
    """
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    if len(expected) == 0 or len(actual) == 0:
        return 0.0
    edges = np.quantile(expected, np.linspace(0, 1, bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    e = np.histogram(expected, bins=edges)[0] / len(expected)
    a = np.histogram(actual, bins=edges)[0] / len(actual)
    e = np.clip(e, _EPS, None)
    a = np.clip(a, _EPS, None)
    return float(np.sum((a - e) * np.log(a / e)))


def ks_statistic(a, b) -> float:
    """Two-sample Kolmogorov-Smirnov statistic: max CDF gap (0=identical, 1=disjoint)."""
    a = np.sort(np.asarray(a, dtype=float))
    b = np.sort(np.asarray(b, dtype=float))
    if len(a) == 0 or len(b) == 0:
        return 0.0
    grid = np.concatenate([a, b])
    cdf_a = np.searchsorted(a, grid, side="right") / len(a)
    cdf_b = np.searchsorted(b, grid, side="right") / len(b)
    return float(np.max(np.abs(cdf_a - cdf_b)))


@dataclass
class ScoreMonitor:
    """Tracks the reference score distribution and reports drift on live batches."""

    reference: np.ndarray
    psi_threshold: float = 0.25

    def __post_init__(self):
        self.reference = np.asarray(self.reference, dtype=float)

    def summary(self, scores) -> dict:
        s = np.asarray(scores, dtype=float)
        if len(s) == 0:
            return {"n": 0, "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
        return {
            "n": int(len(s)), "mean": float(s.mean()), "std": float(s.std()),
            "min": float(s.min()), "max": float(s.max()),
        }

    def drift(self, scores) -> dict:
        return {
            "psi": psi(self.reference, scores),
            "ks": ks_statistic(self.reference, scores),
        }

    def is_drifted(self, scores) -> bool:
        return psi(self.reference, scores) > self.psi_threshold
