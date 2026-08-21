"""Resource manager: per-mission budgets and their enforcement policy.

A long-horizon agent must not burn unbounded money or time. Each mission can
carry a `Budget` (USD, tokens, wall-clock seconds, tool calls, LLM calls); the
manager accumulates `Usage` and reports a single decision:

- **OK** — under the soft threshold, proceed normally.
- **DOWNGRADE** — crossed the soft threshold (default 80%): keep going but on a
  cheaper footing (the model router uses this on Day 9 to drop a tier).
- **TERMINATE** — a budget is exhausted; the mission should be stopped.

The decision is the **max utilization across all set dimensions**, so whichever
budget is tightest governs. Everything is deterministic and unit-testable; wiring
it into the tick (and persisting usage) is Day 11.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True)
class Budget:
    """Per-mission limits. `None` means that dimension is unbounded."""

    max_usd: float | None = None
    max_tokens: int | None = None
    max_seconds: float | None = None
    max_tool_calls: int | None = None
    max_llm_calls: int | None = None


@dataclass
class Usage:
    """Running consumption (time is tracked separately via the start clock)."""

    usd: float = 0.0
    tokens: int = 0
    tool_calls: int = 0
    llm_calls: int = 0


class BudgetStatus(str, Enum):  # noqa: UP042 - str+Enum for portable JSON values
    OK = "ok"
    DOWNGRADE = "downgrade"
    TERMINATE = "terminate"


@dataclass
class ResourceManager:
    budget: Budget = field(default_factory=Budget)
    usage: Usage = field(default_factory=Usage)
    started_at: float = field(default_factory=time.time)

    def record(
        self, *, usd: float = 0.0, tokens: int = 0,
        tool_calls: int = 0, llm_calls: int = 0,
    ) -> None:
        """Add consumption from a step (an LLM call, a tool call, etc.)."""
        self.usage.usd += usd
        self.usage.tokens += tokens
        self.usage.tool_calls += tool_calls
        self.usage.llm_calls += llm_calls

    def elapsed(self, now: float | None = None) -> float:
        return (time.time() if now is None else now) - self.started_at

    def _ratios(self, now: float | None = None) -> list[float]:
        b, u = self.budget, self.usage
        pairs = [
            (b.max_usd, u.usd),
            (b.max_tokens, u.tokens),
            (b.max_seconds, self.elapsed(now)),
            (b.max_tool_calls, u.tool_calls),
            (b.max_llm_calls, u.llm_calls),
        ]
        return [used / limit for limit, used in pairs if limit]

    def utilization(self, now: float | None = None) -> float:
        """Fraction of the tightest budget consumed (0.0 when no budget set)."""
        ratios = self._ratios(now)
        return max(ratios) if ratios else 0.0

    def evaluate(self, now: float | None = None, soft: float = 0.8) -> BudgetStatus:
        """Policy decision from current utilization."""
        u = self.utilization(now)
        if u >= 1.0:
            return BudgetStatus.TERMINATE
        if u >= soft:
            return BudgetStatus.DOWNGRADE
        return BudgetStatus.OK

    def exceeded(self, now: float | None = None) -> bool:
        return self.utilization(now) >= 1.0

    def remaining(self, now: float | None = None) -> dict[str, float | None]:
        """Headroom per dimension; `None` where that dimension is unbounded."""
        b, u = self.budget, self.usage
        return {
            "usd": None if b.max_usd is None else b.max_usd - u.usd,
            "tokens": None if b.max_tokens is None else b.max_tokens - u.tokens,
            "seconds": None if b.max_seconds is None else b.max_seconds - self.elapsed(now),
            "tool_calls": None if b.max_tool_calls is None else b.max_tool_calls - u.tool_calls,
            "llm_calls": None if b.max_llm_calls is None else b.max_llm_calls - u.llm_calls,
        }


def budget_from_meta(meta: dict | None) -> Budget:
    """Build a Budget from a mission's `meta['budget']` spec (all keys optional)."""
    spec = (meta or {}).get("budget") or {}
    return Budget(
        max_usd=spec.get("max_usd"),
        max_tokens=spec.get("max_tokens"),
        max_seconds=spec.get("max_seconds"),
        max_tool_calls=spec.get("max_tool_calls"),
        max_llm_calls=spec.get("max_llm_calls"),
    )
