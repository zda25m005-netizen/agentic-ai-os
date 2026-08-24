"""Metrics, models, and the training smoke — all numpy, CI-safe."""
import numpy as np

from ml.anomaly.data import GeneratorConfig, generate, split
from ml.anomaly.features import FeaturePipeline, to_xy
from ml.anomaly.metrics import (
    average_precision,
    precision_recall_f1,
    roc_auc,
)
from ml.anomaly.models import (
    AutoencoderNP,
    GaussianScorer,
    LogisticRegressionNP,
    Standardizer,
    build_models,
)
from ml.anomaly.tracking import Tracker
from ml.anomaly.train import train_all

CFG = GeneratorConfig(n_transactions=2500, n_users=80, anomaly_rate=0.08, seed=5)


def _splits():
    return split(generate(CFG), seed=5)


def _xy(pipe, rows, std=None):
    x, y = to_xy(pipe, rows)
    x = np.asarray(x, float)
    y = np.asarray(y)
    return (std.transform(x) if std else x), y


# --- metrics ---

def test_roc_auc_extremes():
    assert roc_auc([0, 0, 1, 1], [0.1, 0.2, 0.3, 0.4]) == 1.0
    assert roc_auc([0, 0, 1, 1], [0.4, 0.3, 0.2, 0.1]) == 0.0


def test_average_precision_perfect():
    assert average_precision([0, 0, 1, 1], [0.1, 0.2, 0.3, 0.4]) == 1.0


def test_precision_recall_f1():
    p, r, f1 = precision_recall_f1([1, 1, 0, 0], [1, 0, 0, 0])
    assert p == 1.0 and r == 0.5
    assert abs(f1 - 2 / 3) < 1e-9


def test_roc_auc_handles_single_class():
    assert np.isnan(roc_auc([0, 0, 0], [0.1, 0.2, 0.3]))


# --- models ---

def test_each_model_separates_anomalies():
    s = _splits()
    pipe = FeaturePipeline().fit(s.train)
    x_tr, y_tr = _xy(pipe, s.train)
    std = Standardizer().fit(x_tr)
    x_tr, y_tr = std.transform(x_tr), y_tr
    x_va, y_va = _xy(pipe, s.val, std)

    for model, floor in [
        (GaussianScorer(), 0.85),
        (LogisticRegressionNP(), 0.85),
        (AutoencoderNP(), 0.75),
    ]:
        model.fit(x_tr, y_tr)
        auc = roc_auc(y_va, model.score(x_va))
        assert auc > floor, f"{model.name} ROC-AUC {auc:.3f} below {floor}"


def test_build_models_has_at_least_three():
    names = [m.name for m in build_models()]
    assert len(names) >= 3
    assert {"gaussian", "logreg", "autoencoder"} <= set(names)


def test_sklearn_wrappers_are_picklable_by_reference():
    # regression: the registry pickles the winner; local classes can't pickle.
    # Pickling an unfitted wrapper needs only that the class is module-level.
    import pickle

    from ml.anomaly.models import GradientBoostingModel, IsolationForestModel

    for cls in (GradientBoostingModel, IsolationForestModel):
        assert pickle.loads(pickle.dumps(cls)) is cls          # class by reference
        assert pickle.loads(pickle.dumps(cls())).name == cls.name  # unfitted instance


# --- training + tracking ---

def test_train_all_compares_and_ranks_models():
    s = _splits()
    tracker = Tracker(out="/tmp/anom_runs_test")
    results = train_all(s.train, s.val, tracker=tracker, seed=5)

    assert len(results) >= 3
    for r in results:
        assert np.isfinite(r["roc_auc"]) and np.isfinite(r["pr_auc"])
    # sorted by PR-AUC descending
    prs = [r["pr_auc"] for r in results]
    assert prs == sorted(prs, reverse=True)
    # every model logged a run
    assert len(tracker.runs) == len(results)
    assert tracker.runs[0].metrics.get("roc_auc") is not None


def test_tracker_local_backend_records():
    t = Tracker(out="/tmp/anom_runs_test2")
    with t.run("demo") as run:
        run.log_params({"model": "demo"})
        run.log_metrics({"roc_auc": 0.9})
    assert t.backend in ("mlflow", "local-json")
    assert t.runs[0].metrics["roc_auc"] == 0.9
