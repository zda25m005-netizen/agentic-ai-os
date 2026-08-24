"""Evaluation: threshold selection, calibration, test-set report, registry."""
import numpy as np

from ml.anomaly.data import GeneratorConfig, generate, split
from ml.anomaly.evaluate import (
    best_f1_threshold,
    brier_score,
    evaluate_all,
    threshold_at_recall,
)
from ml.anomaly.models import GaussianScorer
from ml.anomaly.registry import latest_version, load_model, save_model

CFG = GeneratorConfig(n_transactions=2400, n_users=80, anomaly_rate=0.08, seed=9)


# --- threshold + calibration scorers ---

def test_best_f1_threshold_separates_cleanly():
    y = [0, 0, 1, 1]
    scores = [0.1, 0.2, 0.8, 0.9]
    thr, f1 = best_f1_threshold(y, scores)
    assert f1 == 1.0
    assert 0.2 < thr <= 0.8


def test_threshold_at_recall_meets_target():
    y = np.array([0, 0, 1, 1])
    scores = np.array([0.1, 0.2, 0.8, 0.9])
    thr = threshold_at_recall(y, scores, target_recall=1.0)
    preds = (scores >= thr).astype(int)
    assert preds[y == 1].sum() == 2  # both anomalies caught


def test_brier_score_ranges():
    assert brier_score([1, 0], [1.0, 0.0]) == 0.0     # perfect
    assert brier_score([1, 0], [0.0, 1.0]) == 1.0     # worst
    assert brier_score([1, 0], [2.0, 3.0]) is None    # not probabilities


# --- full evaluation ---

def test_evaluate_all_reports_test_metrics_and_winner():
    s = split(generate(CFG), seed=9)
    pipe, std, models, results, winner = evaluate_all(s.train, s.val, s.test, seed=9)
    assert len(results) >= 3
    assert winner in {m.name for m in models}
    for r in results:
        assert np.isfinite(r["roc_auc"]) and np.isfinite(r["pr_auc"])
        assert "threshold" in r and 0.0 <= r["precision"] <= 1.0
    # results ordered by test PR-AUC descending
    prs = [r["pr_auc"] for r in results]
    assert prs == sorted(prs, reverse=True)


# --- registry roundtrip ---

def test_registry_versions_and_roundtrip(tmp_path):
    root = str(tmp_path / "registry")
    model = GaussianScorer().fit(np.array([[0.0, 0.0], [1.0, 1.0]]), np.array([0, 0]))
    x = np.array([[5.0, 5.0], [0.1, 0.1]])
    expected = model.score(x)

    v1 = save_model({"model": model}, {"pr_auc": 0.9}, {"model": "gaussian"}, root=root)
    v2 = save_model({"model": model}, {"pr_auc": 0.8}, {"model": "gaussian"}, root=root)
    assert (v1, v2) == (1, 2)
    assert latest_version(root) == 2

    loaded = load_model(root)  # latest
    assert loaded["version"] == 2
    assert loaded["metrics"]["pr_auc"] == 0.8
    np.testing.assert_allclose(loaded["artifact"]["model"].score(x), expected)

    assert load_model(root, version=1)["metrics"]["pr_auc"] == 0.9
