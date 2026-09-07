"""Memory-decision policy (config F) tests.

Covers: deterministic parity with the historical rule set, the learned LinearPolicy's
save/load round-trip and illegal-action clamping, and the get_policy() safe-fallback.
"""

import numpy as np

from app.memory.policy import (
    ADD,
    NOOP,
    UPDATE,
    DeterministicPolicy,
    LinearPolicy,
    get_policy,
)


def test_deterministic_matches_historical_rules():
    p = DeterministicPolicy()
    # near-duplicate -> NOOP
    assert (
        p.decide({"best_sim": 0.9, "is_correction": False, "has_best": True, "exact_match": False})
        == NOOP
    )
    # exact match -> NOOP even at low sim
    assert (
        p.decide({"best_sim": 0.1, "is_correction": False, "has_best": True, "exact_match": True})
        == NOOP
    )
    # correction above the correction threshold -> UPDATE
    assert (
        p.decide({"best_sim": 0.4, "is_correction": True, "has_best": True, "exact_match": False})
        == UPDATE
    )
    # correction but too dissimilar -> ADD (not an update of an unrelated fact)
    assert (
        p.decide({"best_sim": 0.1, "is_correction": True, "has_best": True, "exact_match": False})
        == ADD
    )
    # novel -> ADD
    assert (
        p.decide(
            {"best_sim": 0.05, "is_correction": False, "has_best": False, "exact_match": False}
        )
        == ADD
    )


def test_linear_policy_save_load_roundtrip(tmp_path):
    w = np.arange(18, dtype=float).reshape(3, 6)
    pol = LinearPolicy(w)
    path = tmp_path / "w.json"
    pol.save(path)
    loaded = LinearPolicy.load(path)
    assert np.allclose(loaded.W, w)


def test_linear_policy_clamps_illegal_actions():
    # Force weights that would prefer UPDATE, but with no similar record it must ADD.
    w = np.zeros((3, 6))
    w[UPDATE, 0] = 10.0  # huge bias toward UPDATE
    pol = LinearPolicy(w)
    assert (
        pol.decide(
            {"best_sim": 0.0, "is_correction": True, "has_best": False, "exact_match": False}
        )
        == ADD
    )
    # with a similar record present, UPDATE is allowed
    assert (
        pol.decide({"best_sim": 0.4, "is_correction": True, "has_best": True, "exact_match": False})
        == UPDATE
    )


def test_get_policy_falls_back_to_deterministic(tmp_path):
    # rl mode but no weights file -> deterministic
    p = get_policy("rl", weights_path=tmp_path / "missing.json")
    assert isinstance(p, DeterministicPolicy)
    # non-rl modes -> deterministic
    assert isinstance(get_policy("deterministic"), DeterministicPolicy)
    assert isinstance(get_policy("llm"), DeterministicPolicy)


def test_get_policy_loads_rl_weights(tmp_path):
    path = tmp_path / "w.json"
    LinearPolicy(np.zeros((3, 6))).save(path)
    assert isinstance(get_policy("rl", weights_path=path), LinearPolicy)


def test_get_policy_bad_weights_falls_back(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{ not valid json")
    assert isinstance(get_policy("rl", weights_path=path), DeterministicPolicy)
