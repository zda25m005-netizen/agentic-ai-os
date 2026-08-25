"""REST surface for the served anomaly model.

`POST /anomaly/score` runs a transaction through the promoted model and records
Prometheus metrics; `GET /anomaly/status` reports whether a model is loaded;
`POST /anomaly/drift` computes PSI/KS of a batch of scores vs a reference and
publishes the PSI gauge. Degrades to 503 when the registry has no model.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.obs import metrics as obs_metrics
from ml.anomaly.monitoring import ScoreMonitor
from ml.anomaly.serving import Scorer

router = APIRouter(prefix="/anomaly", tags=["anomaly"])

_cache: dict = {}


def get_scorer() -> Scorer | None:
    """Lazily load the promoted model once; None if the registry is empty."""
    if "scorer" not in _cache:
        try:
            _cache["scorer"] = Scorer.from_registry()
        except Exception:
            _cache["scorer"] = None
    return _cache["scorer"]


class TransactionIn(BaseModel):
    amount: float
    user_id: int = 0
    timestamp: float = 0.0
    merchant_id: int = 0
    merchant_category: str = ""
    country: str = ""
    hour: int | None = None
    day_of_week: int | None = None
    seconds_since_prev: float = 0.0

    def to_dict(self) -> dict:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class DriftIn(BaseModel):
    reference: list[float]
    scores: list[float]


@router.get("/status")
def status(scorer: Scorer | None = Depends(get_scorer)) -> dict:  # noqa: B008
    if scorer is None:
        return {"model_available": False}
    return {
        "model_available": True, "model": scorer.model_name,
        "version": scorer.version, "threshold": scorer.threshold,
    }


@router.post("/score")
def score(
    txn: TransactionIn, scorer: Scorer | None = Depends(get_scorer)  # noqa: B008
) -> dict:
    if scorer is None:
        raise HTTPException(503, "no anomaly model in registry; run ml.anomaly.evaluate")
    result = scorer.score(txn.to_dict())
    obs_metrics.observe_anomaly(result.score, result.is_anomaly)
    return result.as_dict()


@router.post("/drift")
def drift(req: DriftIn) -> dict:
    monitor = ScoreMonitor(reference=req.reference)
    d = monitor.drift(req.scores)
    obs_metrics.set_drift_psi(d["psi"])
    return {**d, "drifted": monitor.is_drifted(req.scores),
            "summary": monitor.summary(req.scores)}
