"""Anomaly-scan tool: lets an agent score a transaction and get evidence.

This is where the ML model plugs into the mission runtime — an agent can call
`anomaly_scan` on a transaction and receive a structured "evidence" record
(is_anomaly, score, threshold, model version) to reason over, exactly the
"anomaly detected -> evidence" step of the pipeline. Falls back to a clear
message when no model has been promoted to the registry yet.
"""
from __future__ import annotations

from app.tools.registry import tool

_PARAMS = {
    "type": "object",
    "properties": {
        "amount": {"type": "number", "description": "transaction amount"},
        "user_id": {"type": "integer"},
        "timestamp": {"type": "number", "description": "unix seconds"},
        "merchant_category": {"type": "string"},
        "country": {"type": "string"},
        "seconds_since_prev": {"type": "number"},
    },
    "required": ["amount"],
}

_scorer_cache: dict = {}


def _scorer():
    if "s" not in _scorer_cache:
        try:
            from ml.anomaly.serving import Scorer
            _scorer_cache["s"] = Scorer.from_registry()
        except Exception:
            _scorer_cache["s"] = None
    return _scorer_cache["s"]


@tool(
    name="anomaly_scan",
    description="Score a financial transaction with the trained anomaly model and "
    "return evidence (is_anomaly, score, threshold, model version).",
    parameters=_PARAMS,
)
async def anomaly_scan(**txn) -> str:
    scorer = _scorer()
    if scorer is None:
        return "anomaly model not available (no version in registry)"
    from ml.anomaly.serving import anomaly_evidence
    ev = anomaly_evidence(txn, scorer)
    verdict = "ANOMALY" if ev["is_anomaly"] else "normal"
    return (f"{verdict}: score={ev['score']} (threshold={ev['threshold']}, "
            f"model={ev['model']} v{ev['model_version']})")
