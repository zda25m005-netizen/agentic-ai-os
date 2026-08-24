"""Anomaly-detection models with a uniform interface.

Every model implements `.fit(X, y)` and `.score(X) -> higher means more
anomalous`, so training/eval can treat them interchangeably. Three real models
are implemented in **pure numpy** so they always run (CI included):

- **GaussianScorer** — unsupervised; per-feature Gaussian fit on normal rows,
  score = summed squared z-distance.
- **LogisticRegressionNP** — supervised linear classifier (numpy gradient
  descent, class-weighted for imbalance).
- **AutoencoderNP** — a small MLP autoencoder trained on normal rows;
  reconstruction error is the anomaly score.

Two more (**IsolationForest**, **GradientBoosting**) are added automatically when
scikit-learn is installed — so a local run compares five models, CI compares three.
"""
from __future__ import annotations

import numpy as np


class Standardizer:
    """Zero-mean, unit-variance scaling, fit on training features only."""

    def fit(self, X: np.ndarray) -> Standardizer:
        X = np.asarray(X, dtype=float)
        self.mu = X.mean(axis=0)
        self.sd = X.std(axis=0)
        self.sd[self.sd == 0] = 1.0
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        return (np.asarray(X, dtype=float) - self.mu) / self.sd

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)


class GaussianScorer:
    name = "gaussian"

    def fit(self, X: np.ndarray, y: np.ndarray | None = None) -> GaussianScorer:
        X = np.asarray(X, dtype=float)
        normal = X[np.asarray(y) == 0] if y is not None else X
        self.mu = normal.mean(axis=0)
        self.var = normal.var(axis=0) + 1e-6
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        return (((X - self.mu) ** 2) / self.var).sum(axis=1)


class LogisticRegressionNP:
    name = "logreg"

    def __init__(self, lr: float = 0.2, epochs: int = 400, l2: float = 1e-4, seed: int = 0):
        self.lr, self.epochs, self.l2, self.seed = lr, epochs, l2, seed

    def fit(self, X: np.ndarray, y: np.ndarray) -> LogisticRegressionNP:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        n, d = X.shape
        self.w = np.zeros(d)
        self.b = 0.0
        # class weights to counter imbalance
        pos = max(y.sum(), 1.0)
        neg = max(n - y.sum(), 1.0)
        wpos, wneg = n / (2 * pos), n / (2 * neg)
        weights = np.where(y == 1, wpos, wneg)
        for _ in range(self.epochs):
            z = np.clip(X @ self.w + self.b, -30, 30)
            p = 1.0 / (1.0 + np.exp(-z))
            g = (p - y) * weights
            self.w -= self.lr * (X.T @ g / n + self.l2 * self.w)
            self.b -= self.lr * g.mean()
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        z = np.clip(np.asarray(X, dtype=float) @ self.w + self.b, -30, 30)
        return 1.0 / (1.0 + np.exp(-z))


class AutoencoderNP:
    name = "autoencoder"

    def __init__(self, hidden: int = 8, lr: float = 0.05, epochs: int = 300, seed: int = 0):
        self.hidden, self.lr, self.epochs, self.seed = hidden, lr, epochs, seed

    def fit(self, X: np.ndarray, y: np.ndarray | None = None) -> AutoencoderNP:
        X = np.asarray(X, dtype=float)
        normal = X[np.asarray(y) == 0] if y is not None else X
        rng = np.random.default_rng(self.seed)
        d, h, n = normal.shape[1], self.hidden, len(normal)
        self.W1 = rng.normal(0, 0.1, (d, h))
        self.b1 = np.zeros(h)
        self.W2 = rng.normal(0, 0.1, (h, d))
        self.b2 = np.zeros(d)
        for _ in range(self.epochs):
            z = np.tanh(normal @ self.W1 + self.b1)
            recon = z @ self.W2 + self.b2
            err = recon - normal
            dW2 = z.T @ err / n
            db2 = err.mean(axis=0)
            dz = (err @ self.W2.T) * (1 - z ** 2)
            dW1 = normal.T @ dz / n
            db1 = dz.mean(axis=0)
            self.W1 -= self.lr * dW1
            self.b1 -= self.lr * db1
            self.W2 -= self.lr * dW2
            self.b2 -= self.lr * db2
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        z = np.tanh(X @ self.W1 + self.b1)
        recon = z @ self.W2 + self.b2
        return ((recon - X) ** 2).mean(axis=1)


# NOTE: these wrappers are defined at MODULE level (not inside the factory) so a
# fitted model is picklable — the registry pickles the winning artifact. sklearn
# is imported lazily inside fit(), so importing this module never requires it.
class IsolationForestModel:
    name = "isolation_forest"

    def fit(self, X, y=None) -> IsolationForestModel:
        from sklearn.ensemble import IsolationForest
        self._m = IsolationForest(random_state=0, contamination="auto").fit(X)
        return self

    def score(self, X):
        return -self._m.score_samples(X)  # higher = more anomalous


class GradientBoostingModel:
    name = "gradient_boosting"

    def fit(self, X, y) -> GradientBoostingModel:
        from sklearn.ensemble import GradientBoostingClassifier
        self._m = GradientBoostingClassifier(random_state=0).fit(X, y)
        return self

    def score(self, X):
        return self._m.predict_proba(X)[:, 1]


def _optional_sklearn_models() -> list:
    """IsolationForest + GradientBoosting instances, only if sklearn is installed."""
    try:
        import sklearn.ensemble  # noqa: F401
    except Exception:
        return []
    return [IsolationForestModel(), GradientBoostingModel()]


def build_models() -> list:
    """All available models: 3 numpy models + sklearn ones when installed."""
    return [GaussianScorer(), LogisticRegressionNP(), AutoencoderNP(), *_optional_sklearn_models()]
