"""Mission + task status enums and the mission state machine.

The state machine is the safety rail for long-running missions: only legal
transitions are allowed, so a paused mission can't jump straight to completed and
a terminal mission can't be revived. Enforced centrally in the repository.
"""
from __future__ import annotations

from enum import Enum


class MissionStatus(str, Enum):  # noqa: UP042 - str+Enum for portable JSON/DB values
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatus(str, Enum):  # noqa: UP042 - str+Enum for portable JSON/DB values
    PENDING = "pending"    # deps not yet satisfied
    READY = "ready"        # deps satisfied, awaiting execution
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


# Allowed mission transitions (current -> {allowed targets}).
_MISSION_TRANSITIONS: dict[MissionStatus, set[MissionStatus]] = {
    MissionStatus.CREATED: {MissionStatus.ACTIVE, MissionStatus.FAILED},
    MissionStatus.ACTIVE: {MissionStatus.PAUSED, MissionStatus.COMPLETED, MissionStatus.FAILED},
    MissionStatus.PAUSED: {MissionStatus.ACTIVE, MissionStatus.FAILED},
    MissionStatus.COMPLETED: set(),
    MissionStatus.FAILED: set(),
}

TERMINAL_STATUSES = {MissionStatus.COMPLETED, MissionStatus.FAILED}


class InvalidTransition(Exception):
    """Raised when an illegal mission state transition is attempted."""


def can_transition(current: MissionStatus, target: MissionStatus) -> bool:
    return target in _MISSION_TRANSITIONS.get(current, set())


def transition(current: MissionStatus, target: MissionStatus) -> MissionStatus:
    """Return `target` if the transition is legal, else raise InvalidTransition."""
    if not can_transition(current, target):
        raise InvalidTransition(f"illegal mission transition: {current.value} -> {target.value}")
    return target


def is_terminal(status: MissionStatus) -> bool:
    return status in TERMINAL_STATUSES
