"""Synthetic anomaly dataset: reproducibility, label balance, splits, card."""
from collections import Counter

from ml.anomaly.data import (
    ANOMALY_TYPES,
    NONE,
    GeneratorConfig,
    dataset_card,
    generate,
    split,
)

CFG = GeneratorConfig(n_transactions=3000, n_users=100, anomaly_rate=0.08, seed=7)


def test_generation_is_reproducible():
    a = generate(CFG)
    b = generate(CFG)
    assert [r.as_dict() for r in a] == [r.as_dict() for r in b]


def test_different_seed_changes_data():
    a = generate(CFG)
    b = generate(GeneratorConfig(n_transactions=3000, n_users=100, anomaly_rate=0.08, seed=8))
    assert [r.as_dict() for r in a] != [r.as_dict() for r in b]


def test_label_balance_near_target_rate():
    rows = generate(CFG)
    rate = sum(r.label for r in rows) / len(rows)
    assert abs(rate - CFG.anomaly_rate) < 0.02  # within 2 pts of target


def test_labels_and_types_are_consistent():
    for r in generate(CFG):
        if r.label == 1:
            assert r.anomaly_type in ANOMALY_TYPES
        else:
            assert r.anomaly_type == NONE


def test_all_anomaly_types_present():
    types = {r.anomaly_type for r in generate(CFG) if r.label == 1}
    assert types == set(ANOMALY_TYPES)


def test_amount_spike_and_geo_mismatch_are_real():
    rows = generate(CFG)
    spikes = [r for r in rows if r.anomaly_type == "amount_spike"]
    offh = [r for r in rows if r.anomaly_type == "off_hours"]
    assert all(r.amount > 0 for r in spikes)
    assert all(1 <= r.hour <= 4 for r in offh)  # off-hours forced into 1-4am


def test_split_sizes_and_disjoint():
    rows = generate(CFG)
    s = split(rows, seed=7)
    assert len(s.train) + len(s.val) + len(s.test) == len(rows)
    ids = [r.txn_id for r in s.train + s.val + s.test]
    assert len(set(ids)) == len(rows)  # no overlap, nothing dropped


def test_split_is_stratified():
    rows = generate(CFG)
    s = split(rows, seed=7)
    full = sum(r.label for r in rows) / len(rows)
    for part in (s.train, s.val, s.test):
        rate = sum(r.label for r in part) / len(part)
        assert abs(rate - full) < 0.02  # label ratio preserved across splits


def test_split_is_deterministic():
    rows = generate(CFG)
    a = split(rows, seed=7)
    b = split(rows, seed=7)
    assert [r.txn_id for r in a.train] == [r.txn_id for r in b.train]


def test_dataset_card_summarizes():
    rows = generate(CFG)
    card = dataset_card(rows, CFG)
    assert card["n_transactions"] == len(rows)
    assert card["n_anomalies"] == sum(r.label for r in rows)
    assert Counter(card["anomaly_type_counts"]).keys() == set(ANOMALY_TYPES)
    assert "amount" in card["feature_fields"]
