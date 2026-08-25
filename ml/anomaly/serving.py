"""Serve the promoted anomaly model: raw transaction -> anomaly decision.

Loads a versioned artifact from the registry (model + feature pipeline +
standardizer + threshold) and scores a raw transaction dict end to end. Missing
temporal fields are derived from the timestamp. If the registry is empty the
caller gets a clear error rather than a crash, so the API can degrade gracefully.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ml.anomaly.data import Transaction, _hour_dow
from ml.anomaly.features import FeaturePipeline
from ml.anomaly.models import Standardizer
from ml.anomaly.registry import DEFAULT_ROOT, load_model


def transaction_from_dict(d: dict) -> Transaction:
    """Build a Transaction from a partial dict, deriving/ defaulting missing fields."""
    ts = float(d.get("timestamp", 0.0))
    if "hour" in d and "day_of_week" in d:
        hour, dow = int(d["hour"]), int(d["day_of_week"])
    elif ts:
        hour, dow = _hour_dow(ts)
    else:
        hour, dow = int(d.get("hour", 0)), int(d.get("day_of_week", 0))
    return Transaction(
        txn_id=int(d.get("txn_id", 0)),
        user_id=int(d.get("user_id", 0)),
        timestamp=ts,
        amount=float(d.get("amount", 0.0)),
        merchant_id=int(d.get("merchant_id", 0)),
        merchant_category=str(d.get("merchant_category", "")),
        country=str(d.get("country", "")),
        hour=hour,
        day_of_week=dow,
        is_weekend=bool(d.get("is_weekend", dow >= 5)),
        seconds_since_prev=float(d.get("seconds_since_prev", 0.0)),
        label=int(d.get("label", 0)),
        anomaly_type=str(d.get("anomaly_type", "none")),
    )


@dataclass
class AnomalyResult:
    score: float
    is_anomaly: bool
    threshold: float
    model: str
    version: int | None

    def as_dict(self) -> dict:
        return {
            "score": self.score, "is_anomaly": self.is_anomaly,
            "threshold": self.threshold, "model": self.model, "version": self.version,
        }


@dataclass
class Scorer:
    pipeline: FeaturePipeline
    standardizer: Standardizer
    model: object
    threshold: float
    model_name: str = "model"
    version: int | None = None

    @classmethod
    def from_registry(cls, root: str = DEFAULT_ROOT, version: int | None = None) -> Scorer:
        rec = load_model(root, version)  # raises FileNotFoundError if empty
        a = rec["artifact"]
        return cls(
            pipeline=a["pipeline"], standardizer=a["standardizer"],
            model=a["model"], threshold=float(a["threshold"]),
            model_name=rec["meta"].get("model", "model"), version=rec["version"],
        )

    def score(self, txn) -> AnomalyResult:
        t = txn if isinstance(txn, Transaction) else transaction_from_dict(txn)
        x = self.standardizer.transform(np.array([self.pipeline.transform_row(t)], dtype=float))
        s = float(np.asarray(self.model.score(x))[0])
        return AnomalyResult(
            score=s, is_anomaly=s >= self.threshold, threshold=self.threshold,
            model=self.model_name, version=self.version,
        )


def anomaly_evidence(txn: dict, scorer: Scorer) -> dict:
    """Score a transaction and return a mission-ready 'evidence' record."""
    r = scorer.score(txn)
    verdict = "anomalous" if r.is_anomaly else "normal"
    return {
        "claim": f"transaction is {verdict}",
        "is_anomaly": r.is_anomaly,
        "score": round(r.score, 4),
        "threshold": round(r.threshold, 4),
        "model": r.model,
        "model_version": r.version,
    }
