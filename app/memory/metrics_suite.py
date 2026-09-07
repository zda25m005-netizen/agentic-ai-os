"""Honest, *separated* memory metrics (config G).

A learned memory policy can be good at one thing and bad at another, so collapsing
everything into a single "accuracy" number is misleading. This module keeps the distinct
quantities distinct — each is computed independently and reported under its own name:

    policy_action_accuracy   — did the policy pick the right memory OP (STORE/UPDATE/…)?
    retrieval_metrics        — precision / recall / F1 of what it pulled back
    temporal_update_accuracy — on corrections, did the new value win and the stale one go?
    task_success             — did the downstream task actually get answered?
    token_efficiency         — how many context tokens did the memory cost vs. a baseline?
    latency_stats            — wall-clock cost of the memory decisions

Nothing here fabricates a benchmark: each function takes measured inputs and returns the
arithmetic. ``policy_action_accuracy`` is explicitly a *policy action* metric on the local
decision environment — it is NOT retrieval accuracy or task success, and must never be
reported as "memory accuracy".
"""

from __future__ import annotations

from collections import defaultdict

from app.memory.trajectory.actions import OPS, MemoryOp


# --- 1. policy action accuracy -------------------------------------------------
def policy_action_accuracy(predicted: list[int], optimal: list[int]) -> dict:
    """Fraction of decisions where the predicted OP equals the labelled optimal OP.

    Returns overall accuracy plus a per-op breakdown (so a policy that only ever STOREs
    can't hide behind a high average). This is a *policy action* metric only.
    """
    if not optimal:
        return {"metric": "policy_action_accuracy", "accuracy": 0.0, "n": 0, "per_op": {}}
    correct = sum(1 for p, o in zip(predicted, optimal, strict=False) if p == o)
    per_total: dict[int, int] = defaultdict(int)
    per_correct: dict[int, int] = defaultdict(int)
    for p, o in zip(predicted, optimal, strict=False):
        per_total[o] += 1
        if p == o:
            per_correct[o] += 1
    per_op = {
        OPS[o]: round(per_correct[o] / per_total[o], 4) for o in sorted(per_total) if per_total[o]
    }
    return {
        "metric": "policy_action_accuracy",
        "accuracy": round(correct / len(optimal), 4),
        "n": len(optimal),
        "per_op": per_op,
    }


# --- 2. retrieval quality ------------------------------------------------------
def retrieval_metrics(retrieved: list, gold: list) -> dict:
    """Precision / recall / F1 of a retrieved set against the gold set (order-free)."""
    r, g = set(retrieved), set(gold)
    tp = len(r & g)
    precision = tp / len(r) if r else 0.0
    recall = tp / len(g) if g else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "metric": "memory_retrieval_accuracy",
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


# --- 3. temporal update accuracy ----------------------------------------------
def temporal_update_accuracy(cases: list[dict]) -> dict:
    """On correction cases, fraction where the new value is current AND stale is gone.

    Each case: ``{"new_current": bool, "stale_leaked": bool}``. A case counts as correct
    only when the new value is retrievable and the superseded value did not leak.
    """
    if not cases:
        return {"metric": "temporal_update_accuracy", "accuracy": 0.0, "n": 0}
    ok = sum(1 for c in cases if c.get("new_current") and not c.get("stale_leaked"))
    return {
        "metric": "temporal_update_accuracy",
        "accuracy": round(ok / len(cases), 4),
        "n": len(cases),
    }


# --- 4. task success -----------------------------------------------------------
def task_success(results: list[bool]) -> dict:
    """Fraction of downstream tasks whose answer was judged correct."""
    if not results:
        return {"metric": "task_success", "success_rate": 0.0, "n": 0}
    return {
        "metric": "task_success",
        "success_rate": round(sum(1 for r in results if r) / len(results), 4),
        "n": len(results),
    }


# --- 5. token efficiency -------------------------------------------------------
def token_efficiency(tokens_used: int, baseline_tokens: int) -> dict:
    """How many context tokens the memory cost vs. a no-compression baseline.

    ``savings`` is the fraction of baseline tokens avoided (higher is better); ``ratio`` is
    used/baseline. A baseline of 0 yields neutral values rather than a division error.
    """
    if baseline_tokens <= 0:
        return {
            "metric": "token_efficiency",
            "tokens_used": tokens_used,
            "ratio": 1.0,
            "savings": 0.0,
        }
    ratio = tokens_used / baseline_tokens
    return {
        "metric": "token_efficiency",
        "tokens_used": tokens_used,
        "baseline_tokens": baseline_tokens,
        "ratio": round(ratio, 4),
        "savings": round(1.0 - ratio, 4),
    }


# --- 6. latency ----------------------------------------------------------------
def latency_stats(latencies_ms: list[float]) -> dict:
    """Mean / p50 / p95 of measured decision latencies (milliseconds)."""
    if not latencies_ms:
        return {"metric": "latency", "mean_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "n": 0}
    xs = sorted(latencies_ms)
    n = len(xs)

    def pct(p: float) -> float:
        return xs[min(n - 1, int(p * n))]

    return {
        "metric": "latency",
        "mean_ms": round(sum(xs) / n, 3),
        "p50_ms": round(pct(0.50), 3),
        "p95_ms": round(pct(0.95), 3),
        "n": n,
    }


# --- convenience: score a six-action policy on the trajectory env --------------
def evaluate_policy_on_env(policy, env) -> dict:
    """Run a ``policy.act(state)`` over an env and report policy_action_accuracy.

    Clearly scoped: this measures the *policy action* decision only. Retrieval, temporal
    update, task success, token, and latency metrics are computed elsewhere from their own
    measured inputs — this function does not conflate them.
    """
    optimal = [int(s["optimal"]) for s in env.states()]
    predicted = [int(MemoryOp(policy.act(s))) for s in env.states()]
    return policy_action_accuracy(predicted, optimal)
