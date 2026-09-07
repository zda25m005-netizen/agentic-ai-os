"""RL memory policy training (config F) tests — env, GRPO, and train.run().

All seeded, so training is reproducible and fast (pure numpy, no torch).
"""

import numpy as np

from app.memory.policy import ADD, DeterministicPolicy, LinearPolicy
from app.memory.rl.env import LABELS, MemoryDecisionEnv, reward
from app.memory.rl.grpo import GRPOTrainer
from app.memory.rl.train import run


def test_env_is_labelled_and_reproducible():
    a = MemoryDecisionEnv(n=50, seed=0).states()
    b = MemoryDecisionEnv(n=50, seed=0).states()
    assert len(a) == 50
    assert all(s["optimal"] in (0, 1, 2) for s in a)
    assert all(s["kind"] in LABELS for s in a)
    assert np.allclose(a[0]["x"], b[0]["x"])  # same seed -> same data


def test_reward_shaping_penalises_stale_leak_most():
    # optimal is UPDATE (a correction). ADD keeps the stale fact -> the worst error.
    state = {"optimal": 1, "feats": {"has_best": True}}
    assert reward(state, 1) == 1.0  # correct UPDATE
    assert reward(state, 2) == -1.0  # ADD -> stale leak
    # illegal action (needs a record but none present) is strongly penalised
    illegal = {"optimal": 2, "feats": {"has_best": False}}
    assert reward(illegal, 0) == -1.0


def test_grpo_improves_reward_and_learns_policy():
    env = MemoryDecisionEnv(n=400, seed=0)
    trainer = GRPOTrainer(group_size=8, lr=0.3, seed=0)
    report = trainer.train(env, epochs=40)
    # group-relative policy gradient should raise mean greedy reward substantially
    assert report["reward_last"] > report["reward_first"] + 0.4
    # and recover the optimal decision on most states
    assert report["final_accuracy"] >= 0.9


def test_trained_policy_agrees_with_deterministic_on_clear_cases():
    env = MemoryDecisionEnv(n=400, seed=0)
    trainer = GRPOTrainer(group_size=8, lr=0.3, seed=0)
    trainer.train(env, epochs=40)
    learned = trainer.policy()
    det = DeterministicPolicy()
    # on unambiguous novel facts, both should ADD
    novel = {"best_sim": 0.02, "is_correction": False, "has_best": False, "exact_match": False}
    assert learned.decide(novel) == det.decide(novel) == ADD


def test_train_run_saves_weights(tmp_path):
    out = tmp_path / "policy.json"
    report = run(str(out), epochs=20, n=200, seed=0)
    assert out.exists()
    assert report["weights_path"] == str(out)
    assert report["final_accuracy"] >= 0.8
    # saved file loads back into a usable policy
    LinearPolicy.load(out)
