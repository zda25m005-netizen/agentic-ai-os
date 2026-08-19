"""Structured objective — what a mission is actually trying to achieve.

A raw goal ("monitor Company X for 30 days, notify me only on strong evidence")
is turned into this typed object so the runtime knows the success criteria, the
constraints, when to notify the user, and the time horizon.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# one_shot = answer once; monitoring = recurring watch; investigation = dig until resolved
HORIZONS = ("one_shot", "monitoring", "investigation")


@dataclass
class Objective:
    summary: str
    success_criteria: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    notify_conditions: list[str] = field(default_factory=list)
    deadline_days: int | None = None
    horizon: str = "one_shot"

    def as_dict(self) -> dict:
        return {
            "summary": self.summary,
            "success_criteria": self.success_criteria,
            "constraints": self.constraints,
            "notify_conditions": self.notify_conditions,
            "deadline_days": self.deadline_days,
            "horizon": self.horizon,
        }
