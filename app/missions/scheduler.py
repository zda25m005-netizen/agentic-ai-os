"""Agent scheduler: decide which mission runs first, deterministically.

The worker can have many drivable missions at once; under contention we must
pick a defensible order. This is pure systems engineering — a scoring function,
not an LLM call. Each mission gets a score from four terms:

- **priority** — the caller's explicit priority (dominant term).
- **deadline urgency** — closer deadlines score higher; an overdue mission is
  pinned to the maximum so it can't be starved by lower-priority work.
- **age** — a small boost that grows with time waiting, so a low-priority mission
  eventually runs instead of starving forever.
- **value** — an optional expected-value hint from mission metadata.

Ordering is deterministic: ties break by ascending mission id, so the same input
always yields the same order (which is what the test asserts and what makes the
scheduler debuggable).
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from app.missions.models import Mission

_OVERDUE_URGENCY = 2.0  # an overdue deadline outranks any not-yet-due one


@dataclass(frozen=True)
class SchedulerWeights:
    priority: float = 10.0
    deadline: float = 5.0
    age: float = 0.1  # per hour waiting
    value: float = 1.0


DEFAULT_WEIGHTS = SchedulerWeights()


def _deadline_urgency(mission: Mission, now: float) -> float:
    """0 when no deadline, →1 as it approaches, 2.0 once overdue."""
    if mission.deadline is None:
        return 0.0
    time_left = mission.deadline - now
    if time_left <= 0:
        return _OVERDUE_URGENCY
    days_left = time_left / 86400.0
    return 1.0 / (1.0 + days_left)  # in (0, 1)


def score_mission(
    mission: Mission, now: float | None = None, weights: SchedulerWeights = DEFAULT_WEIGHTS
) -> float:
    """Deterministic scheduling score; higher runs first."""
    now = time.time() if now is None else now
    age_hours = max(0.0, (now - mission.created_at) / 3600.0)
    value = float(mission.meta.get("value", 0.0)) if mission.meta else 0.0
    return (
        weights.priority * mission.priority
        + weights.deadline * _deadline_urgency(mission, now)
        + weights.age * age_hours
        + weights.value * value
    )


def order_missions(
    missions: list[Mission],
    now: float | None = None,
    weights: SchedulerWeights = DEFAULT_WEIGHTS,
) -> list[Mission]:
    """Return missions in run order: highest score first, ties by ascending id."""
    now = time.time() if now is None else now
    return sorted(
        missions,
        key=lambda m: (-score_mission(m, now, weights), m.id),
    )


def pick_next(
    missions: list[Mission],
    now: float | None = None,
    weights: SchedulerWeights = DEFAULT_WEIGHTS,
) -> Mission | None:
    """The single highest-scoring mission, or None if the list is empty."""
    ordered = order_missions(missions, now, weights)
    return ordered[0] if ordered else None
