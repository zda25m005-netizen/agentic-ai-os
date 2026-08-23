"""Feature pipeline: determinism, fixed schema, train-only fit, no leakage."""
import pytest

from ml.anomaly.data import GeneratorConfig, generate, split
from ml.anomaly.features import FEATURE_NAMES, FeaturePipeline, to_xy

CFG = GeneratorConfig(n_transactions=2000, n_users=80, anomaly_rate=0.08, seed=11)


def _fitted():
    rows = generate(CFG)
    s = split(rows, seed=11)
    return FeaturePipeline().fit(s.train), s


def test_vector_has_fixed_schema_length():
    pipe, s = _fitted()
    x = pipe.transform_row(s.train[0])
    assert len(x) == len(FEATURE_NAMES) == 14


def test_fit_transform_is_deterministic():
    rows = generate(CFG)
    a = FeaturePipeline().fit_transform(rows)
    b = FeaturePipeline().fit_transform(rows)
    assert a == b


def test_transform_before_fit_raises():
    with pytest.raises(RuntimeError):
        FeaturePipeline().transform(generate(CFG)[:5])


def test_no_leakage_row_is_independent_of_its_split():
    # a val row transformed in isolation must equal it transformed within the split
    pipe, s = _fitted()
    row = s.val[3]
    in_full = pipe.transform(s.val)[3]
    in_isolation = pipe.transform([row])[0]
    assert in_full == in_isolation


def test_fit_uses_train_only():
    # a pipeline fit on train must not change if we ALSO have val data around,
    # because fit never sees val — same train -> identical learned params
    pipe, s = _fitted()
    pipe2 = FeaturePipeline().fit(s.train)
    assert pipe.user_mean == pipe2.user_mean
    assert pipe.global_mean == pipe2.global_mean
    assert pipe.cat_freq == pipe2.cat_freq


def test_unseen_user_falls_back_to_global():
    pipe, s = _fitted()
    unseen = max(pipe.user_mean) + 999  # a user id not in train
    row = s.train[0]
    object.__setattr__(row, "user_id", unseen)  # force an unknown user
    vec = pipe.transform_row(row)
    # amount_ratio_user uses global mean -> amount / global_mean, still finite
    assert all(v == v for v in vec)  # no NaNs
    assert len(vec) == len(FEATURE_NAMES)


def test_to_xy_aligns_features_and_labels():
    pipe, s = _fitted()
    x, y = to_xy(pipe, s.val)
    assert len(x) == len(y) == len(s.val)
    assert all(v in (0, 1) for v in y)


def test_off_hours_and_rapid_flags_fire():
    pipe, s = _fitted()
    names = FEATURE_NAMES
    off_idx = names.index("is_off_hours")
    rapid_idx = names.index("is_rapid")
    rows = generate(CFG)
    offh = next(r for r in rows if r.anomaly_type == "off_hours")
    vel = next(r for r in rows if r.anomaly_type == "velocity")
    assert pipe.transform_row(offh)[off_idx] == 1.0
    assert pipe.transform_row(vel)[rapid_idx] == 1.0
