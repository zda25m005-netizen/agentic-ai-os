"""Self-improving policy engine: strategies that reorder from their own outcomes.

A *policy* is an ordered set of candidate strategies for some context (an error
type, a task category, a tool choice). Each time a strategy is used the engine
records success or failure; strategies are then ranked by a **smoothed success
rate** (Beta(1,1) / Laplace), so a candidate that keeps working is promoted and
one that keeps failing is demoted — the system learns which strategy to try first
without any manual tuning.

The smoothing gives two useful properties: an untried strategy starts at 0.5 (so
it gets explored before a proven-bad one), and a single fluke win/loss doesn't
flip the order. `select` is deterministic (argmax of the smoothed rate), so it's
reproducible and testable; the state serializes to/from a dict for persistence.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Strategy:
    name: str
    successes: int = 0
    attempts: int = 0

    @property
    def rate(self) -> float:
        """Beta(1,1)-smoothed success rate; 0.5 when untried."""
        return (self.successes + 1) / (self.attempts + 2)

    def record(self, success: bool) -> None:
        self.attempts += 1
        if success:
            self.successes += 1


@dataclass
class Policy:
    context: str
    strategies: list[Strategy] = field(default_factory=list)

    def _get(self, name: str) -> Strategy:
        for s in self.strategies:
            if s.name == name:
                return s
        s = Strategy(name)
        self.strategies.append(s)
        return s

    def ordered(self) -> list[Strategy]:
        """Strategies best-first: by smoothed rate, ties toward more evidence."""
        return sorted(self.strategies, key=lambda s: (s.rate, s.attempts), reverse=True)

    def best(self) -> Strategy | None:
        ranked = self.ordered()
        return ranked[0] if ranked else None

    def record(self, name: str, success: bool) -> None:
        self._get(name).record(success)


class PolicyEngine:
    """Holds one policy per context and learns strategy ordering from outcomes."""

    def __init__(self) -> None:
        self._policies: dict[str, Policy] = {}

    def register(self, context: str, candidates: list[str]) -> Policy:
        policy = Policy(context, [Strategy(c) for c in candidates])
        self._policies[context] = policy
        return policy

    def _policy(self, context: str) -> Policy:
        if context not in self._policies:
            self._policies[context] = Policy(context)
        return self._policies[context]

    def select(self, context: str) -> str | None:
        """The current best strategy for a context (None if none registered)."""
        best = self._policy(context).best()
        return best.name if best else None

    def ranked(self, context: str) -> list[str]:
        return [s.name for s in self._policy(context).ordered()]

    def record(self, context: str, strategy: str, success: bool) -> None:
        self._policy(context).record(strategy, success)

    def snapshot(self) -> dict:
        return {
            ctx: {s.name: {"rate": round(s.rate, 4), "attempts": s.attempts,
                           "successes": s.successes}
                  for s in p.ordered()}
            for ctx, p in self._policies.items()
        }

    def to_dict(self) -> dict:
        return {
            ctx: [(s.name, s.successes, s.attempts) for s in p.strategies]
            for ctx, p in self._policies.items()
        }

    @classmethod
    def from_dict(cls, data: dict) -> PolicyEngine:
        engine = cls()
        for ctx, strategies in data.items():
            engine._policies[ctx] = Policy(
                ctx, [Strategy(n, succ, att) for n, succ, att in strategies])
        return engine
