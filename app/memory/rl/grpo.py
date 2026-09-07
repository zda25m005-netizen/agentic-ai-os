"""Minimal GRPO-style trainer for the memory-decision policy (config F).

GRPO's defining move is to replace the value/critic network with a **group-relative
baseline**: for each state, sample a *group* of actions from the current policy, score
them, and standardize the rewards *within the group* to get advantages. The policy is
then nudged toward the above-average actions in each group.

Here the policy is a softmax over ``W · x`` (see ``app.memory.policy.LinearPolicy``), so
the score-function gradient has a closed form:

    ∇_W log π(a|x) = (onehot(a) − π(·|x)) ⊗ x

We add a small entropy bonus (keeps early exploration alive) and an L2 pull toward the
initial weights (a lightweight stand-in for GRPO's KL-to-reference term). Pure numpy;
seeded; converges in well under a second on the local fixtures.

This is honest, small-scale plumbing — a linear policy over a 3-action decision — not a
reproduction of GRPO on an LLM.
"""

from __future__ import annotations

import numpy as np

from app.memory.policy import N_ACTIONS, N_FEATURES, LinearPolicy, _softmax


class GRPOTrainer:
    def __init__(
        self,
        *,
        group_size: int = 8,
        lr: float = 0.3,
        entropy_coef: float = 0.01,
        l2_coef: float = 0.0,
        seed: int = 0,
    ):
        self.group_size = group_size
        self.lr = lr
        self.entropy_coef = entropy_coef
        self.l2_coef = l2_coef
        self.rng = np.random.default_rng(seed)
        self.W = np.zeros((N_ACTIONS, N_FEATURES), dtype=float)
        self.W0 = self.W.copy()

    # --- helpers -------------------------------------------------------------
    def _greedy_accuracy(self, states: list[dict]) -> float:
        correct = 0
        for s in states:
            if int(np.argmax(_softmax(self.W @ s["x"]))) == s["optimal"]:
                correct += 1
        return correct / max(1, len(states))

    def _mean_greedy_reward(self, env, states: list[dict]) -> float:
        total = 0.0
        for s in states:
            a = int(np.argmax(_softmax(self.W @ s["x"])))
            total += env.reward(s, a)
        return total / max(1, len(states))

    # --- training ------------------------------------------------------------
    def train(self, env, *, epochs: int = 40) -> dict:
        states = env.states()
        history = []
        for _ in range(epochs):
            order = self.rng.permutation(len(states))
            grad = np.zeros_like(self.W)
            for i in order:
                s = states[i]
                x = s["x"]
                p = _softmax(self.W @ x)
                # sample a GROUP of actions, score them, standardize within the group
                acts = self.rng.choice(N_ACTIONS, size=self.group_size, p=p)
                rewards = np.array([env.reward(s, int(a)) for a in acts], dtype=float)
                adv = rewards - rewards.mean()
                std = rewards.std()
                if std > 1e-8:
                    adv = adv / std
                for a, A in zip(acts, adv, strict=False):
                    onehot = np.zeros(N_ACTIONS)
                    onehot[a] = 1.0
                    grad += A * np.outer(onehot - p, x)  # ∇ log π(a|x) ⊗ x
                    if self.entropy_coef:  # entropy bonus keeps exploration alive
                        grad += self.entropy_coef * np.outer(-(p * (np.log(p + 1e-12) + 1)), x)
            grad /= max(1, len(states))
            if self.l2_coef:  # KL-to-reference stand-in
                grad -= self.l2_coef * (self.W - self.W0)
            self.W += self.lr * grad
            history.append(
                {
                    "accuracy": self._greedy_accuracy(states),
                    "reward": self._mean_greedy_reward(env, states),
                }
            )
        return {
            "epochs": epochs,
            "group_size": self.group_size,
            "final_accuracy": history[-1]["accuracy"] if history else 0.0,
            "reward_first": history[0]["reward"] if history else 0.0,
            "reward_last": history[-1]["reward"] if history else 0.0,
            "history": history,
        }

    def policy(self) -> LinearPolicy:
        return LinearPolicy(self.W.copy())
