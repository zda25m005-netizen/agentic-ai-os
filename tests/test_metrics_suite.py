"""Honest, separated memory metrics (config G)."""

from app.memory.llm_policy import HeuristicPolicy
from app.memory.metrics_suite import (
    evaluate_policy_on_env,
    latency_stats,
    policy_action_accuracy,
    retrieval_metrics,
    task_success,
    temporal_update_accuracy,
    token_efficiency,
)
from app.memory.trajectory import TrajectoryMemoryEnv


def test_policy_action_accuracy_overall_and_per_op():
    m = policy_action_accuracy([0, 1, 2, 2], [0, 1, 2, 5])
    assert m["metric"] == "policy_action_accuracy"
    assert m["accuracy"] == 0.75
    assert m["per_op"]["STORE"] == 1.0  # op 0 correct
    assert m["per_op"]["NOOP"] == 0.0  # op 5 was predicted as 2


def test_retrieval_metrics_precision_recall_f1():
    m = retrieval_metrics(retrieved=["a", "b", "x"], gold=["a", "b", "c"])
    assert m["metric"] == "memory_retrieval_accuracy"
    assert m["precision"] == round(2 / 3, 4)
    assert m["recall"] == round(2 / 3, 4)
    assert m["f1"] == round(2 / 3, 4)


def test_temporal_update_accuracy_requires_new_current_and_no_stale():
    cases = [
        {"new_current": True, "stale_leaked": False},  # correct
        {"new_current": True, "stale_leaked": True},  # stale leaked -> wrong
        {"new_current": False, "stale_leaked": False},  # new missing -> wrong
    ]
    assert temporal_update_accuracy(cases)["accuracy"] == round(1 / 3, 4)


def test_task_success_and_token_efficiency_and_latency():
    assert task_success([True, True, False, True])["success_rate"] == 0.75
    te = token_efficiency(tokens_used=300, baseline_tokens=1000)
    assert te["ratio"] == 0.3 and te["savings"] == 0.7
    assert token_efficiency(10, 0)["savings"] == 0.0  # no baseline -> neutral
    lat = latency_stats([10, 20, 30, 40, 100])
    assert lat["p50_ms"] == 30 and lat["mean_ms"] == 40.0


def test_metrics_are_distinct_names():
    # the whole point: these are different quantities with different names
    names = {
        policy_action_accuracy([0], [0])["metric"],
        retrieval_metrics(["a"], ["a"])["metric"],
        temporal_update_accuracy([{"new_current": True, "stale_leaked": False}])["metric"],
        task_success([True])["metric"],
        token_efficiency(1, 2)["metric"],
        latency_stats([1.0])["metric"],
    }
    assert names == {
        "policy_action_accuracy",
        "memory_retrieval_accuracy",
        "temporal_update_accuracy",
        "task_success",
        "token_efficiency",
        "latency",
    }


def test_evaluate_policy_on_env_reports_action_accuracy_only():
    env = TrajectoryMemoryEnv(n=50, seed=0)
    m = evaluate_policy_on_env(HeuristicPolicy(), env)
    assert m["metric"] == "policy_action_accuracy"
    assert 0.0 <= m["accuracy"] <= 1.0 and m["n"] == len(env)
