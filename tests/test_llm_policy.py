"""LLM memory policy (config G) — fallback behaviour without the ML stack.

The whole point is that this works with no torch/transformers installed: LLMMemoryPolicy
must degrade to the heuristic, and get_policy(rl, backend=llm) must still return a usable,
resolver-compatible policy. Also verifies the GRPO advantage math and the trainer's clear
error when the heavy stack is absent.
"""

import numpy as np

from app.memory.llm_policy import HeuristicPolicy, LLMMemoryPolicy, backend_available
from app.memory.policy import ADD, NOOP, UPDATE, DeterministicPolicy, get_policy
from app.memory.rl.llm_grpo import LLMGRPOTrainer, group_advantages
from app.memory.trajectory import MemoryOp, TrajectoryMemoryEnv


def test_heuristic_covers_all_six_situations():
    h = HeuristicPolicy()
    assert h.act({"feats": {"is_query": True}, "memory_state": {}}) == MemoryOp.RETRIEVE
    assert (
        h.act({"feats": {"is_correction": True, "sim": 0.4}, "memory_state": {}}) == MemoryOp.UPDATE
    )
    assert h.act({"feats": {"is_noise": True}, "memory_state": {}}) == MemoryOp.DISCARD
    assert h.act({"feats": {"sim": 0.95}, "memory_state": {}}) == MemoryOp.NOOP
    assert h.act({"feats": {"over_budget": True}, "memory_state": {}}) == MemoryOp.SUMMARIZE
    assert h.act({"feats": {"sim": 0.05}, "memory_state": {}}) == MemoryOp.STORE


def test_heuristic_is_a_strong_baseline():
    env = TrajectoryMemoryEnv(n=100, seed=0)
    h = HeuristicPolicy()
    acc = sum(1 for s in env.states() if int(h.act(s)) == s["optimal"]) / len(env)
    assert acc >= 0.9  # strong ceiling the learned policy should approach


def test_llm_policy_falls_back_without_backend():
    pol = LLMMemoryPolicy()
    # In CI the ML stack is absent, so it delegates to the heuristic and never raises.
    assert pol.available() is backend_available()
    op = pol.act({"feats": {"is_query": True}, "memory_state": {}})
    assert op == MemoryOp.RETRIEVE


def test_llm_policy_decide_is_resolver_compatible():
    pol = LLMMemoryPolicy()
    det = DeterministicPolicy()
    for f in (
        {"best_sim": 0.9, "is_correction": False, "has_best": True, "exact_match": False},
        {"best_sim": 0.4, "is_correction": True, "has_best": True, "exact_match": False},
        {"best_sim": 0.02, "is_correction": False, "has_best": False, "exact_match": False},
    ):
        assert pol.decide(f) in (ADD, UPDATE, NOOP)
        assert pol.decide(f) == det.decide(f)  # heuristic agrees on clear cases


def test_get_policy_llm_backend_returns_policy():
    pol = get_policy("rl", backend="llm")
    assert isinstance(pol, LLMMemoryPolicy)
    # non-rl mode still forces deterministic regardless of backend
    assert isinstance(get_policy("deterministic", backend="llm"), DeterministicPolicy)


def test_group_advantages_are_standardized():
    adv = group_advantages([1.0, 0.0, -1.0, 0.0])
    assert abs(float(np.mean(adv))) < 1e-9  # zero-mean
    # constant rewards -> zero advantage (no signal), never NaN
    assert np.allclose(group_advantages([0.5, 0.5, 0.5]), 0.0)


def test_llm_grpo_trainer_errors_clearly_without_stack():
    trainer = LLMGRPOTrainer()
    if backend_available():  # only meaningful when the stack is absent (CI)
        return
    try:
        trainer.train(max_states=1)
        raise AssertionError("expected RuntimeError without torch/transformers/peft")
    except RuntimeError as e:
        assert "finetune" in str(e)
