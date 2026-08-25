"""Serving + monitoring: scorer, drift metrics, API endpoints, mission tool."""
import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from app.api import anomaly as anomaly_api
from app.api.main import app
from ml.anomaly.data import GeneratorConfig, generate, split
from ml.anomaly.evaluate import best_f1_threshold
from ml.anomaly.monitoring import ScoreMonitor, ks_statistic, psi
from ml.anomaly.serving import Scorer, anomaly_evidence, transaction_from_dict
from ml.anomaly.train import features_of, fit_all

CFG = GeneratorConfig(n_transactions=1500, n_users=60, anomaly_rate=0.1, seed=3)


def _scorer() -> Scorer:
    """Train a scorer in-memory (no registry/disk needed)."""
    s = split(generate(CFG), seed=3)
    pipe, std, models = fit_all(s.train, seed=3)
    model = next(m for m in models if m.name == "gaussian")
    x_va, y_va = features_of(pipe, std, s.val)
    thr, _ = best_f1_threshold(y_va, model.score(x_va))
    return Scorer(pipe, std, model, float(thr), model_name="gaussian", version=1)


# --- serving ---

def test_transaction_from_dict_defaults_and_derives():
    t = transaction_from_dict({"amount": 100.0, "timestamp": 1_700_003_600.0})
    assert t.amount == 100.0
    assert 0 <= t.hour <= 23  # derived from timestamp


def test_scorer_flags_obvious_anomaly_over_normal():
    scorer = _scorer()
    normal = scorer.score({"amount": 50.0, "user_id": 1, "country": "US",
                           "merchant_category": "grocery", "seconds_since_prev": 3600})
    huge = scorer.score({"amount": 500000.0, "user_id": 1, "country": "US",
                         "merchant_category": "grocery", "seconds_since_prev": 3600})
    assert huge.score > normal.score  # a massive amount scores more anomalous


def test_anomaly_evidence_shape():
    ev = anomaly_evidence({"amount": 999999.0}, _scorer())
    assert set(ev) >= {"is_anomaly", "score", "threshold", "model", "model_version"}


# --- monitoring ---

def test_psi_zero_for_same_distribution():
    x = np.random.default_rng(0).normal(size=2000)
    assert psi(x, x) < 1e-6


def test_psi_detects_shift():
    rng = np.random.default_rng(0)
    ref = rng.normal(0, 1, 2000)
    shifted = rng.normal(3, 1, 2000)
    assert psi(ref, shifted) > 0.25  # large shift -> significant PSI


def test_ks_extremes():
    a = np.zeros(100)
    b = np.ones(100)
    assert ks_statistic(a, a) == 0.0
    assert ks_statistic(a, b) == 1.0


def test_score_monitor_drift_flag():
    rng = np.random.default_rng(1)
    ref = rng.normal(0, 1, 1000)
    mon = ScoreMonitor(reference=ref, psi_threshold=0.25)
    assert not mon.is_drifted(rng.normal(0, 1, 500))     # same dist
    assert mon.is_drifted(rng.normal(4, 1, 500))         # shifted
    assert mon.summary(ref)["n"] == 1000


# --- API + tool ---

@pytest.fixture
def client():
    app.dependency_overrides[anomaly_api.get_scorer] = _scorer
    transport = ASGITransport(app=app)
    yield AsyncClient(transport=transport, base_url="http://t")
    app.dependency_overrides.clear()


async def test_status_and_score_endpoints(client):
    async with client as c:
        st = await c.get("/anomaly/status")
        assert st.status_code == 200 and st.json()["model_available"] is True

        r = await c.post("/anomaly/score", json={"amount": 500000.0, "country": "US"})
        assert r.status_code == 200
        body = r.json()
        assert set(body) >= {"score", "is_anomaly", "threshold", "model"}


async def test_score_503_when_no_model():
    app.dependency_overrides[anomaly_api.get_scorer] = lambda: None
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.post("/anomaly/score", json={"amount": 10.0})
        assert r.status_code == 503
    app.dependency_overrides.clear()


async def test_drift_endpoint(client):
    async with client as c:
        r = await c.post("/anomaly/drift", json={
            "reference": list(range(100)), "scores": list(range(50, 150))})
        assert r.status_code == 200
        assert "psi" in r.json() and "ks" in r.json()


async def test_anomaly_scan_tool_registered():
    import app.tools  # noqa: F401  (registers tools)
    from app.tools.registry import default_registry
    assert "anomaly_scan" in default_registry._tools
