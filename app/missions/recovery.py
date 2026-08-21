"""Failure recovery: a bounded ladder of strategies for a failing step.

When a task fails, blindly retrying forever is wrong and giving up immediately is
wrong. The recovery engine climbs a fixed ladder — retry, then an alternate tool,
then a cached result, then replanning, then escalate, then terminate — advancing
one rung per failure and always bounded so it can't loop. The error *type* sets
the starting rung (a broken tool skips straight to "alternate tool"; a timeout
starts with a plain retry).

`decide` is the pure policy; `execute_with_recovery` is the async runner that
applies it to a real operation and its fallback handlers.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TypeVar

T = TypeVar("T")


class RecoveryStrategy(str, Enum):  # noqa: UP042 - str+Enum for portable values
    RETRY = "retry"
    ALT_TOOL = "alternate_tool"
    CACHED = "cached"
    REPLAN = "replan"
    ESCALATE = "escalate"
    TERMINATE = "terminate"


# The fixed escalation order. ESCALATE/TERMINATE are the give-up rungs.
LADDER: list[RecoveryStrategy] = [
    RecoveryStrategy.RETRY,
    RecoveryStrategy.ALT_TOOL,
    RecoveryStrategy.CACHED,
    RecoveryStrategy.REPLAN,
    RecoveryStrategy.ESCALATE,
    RecoveryStrategy.TERMINATE,
]

# Where on the ladder a given error type begins.
_START_RUNG: dict[str, int] = {
    "timeout": 0,       # transient -> retry first
    "rate_limit": 0,    # back off and retry
    "tool_error": 1,    # the tool is broken -> alternate tool
    "not_found": 2,     # try a cached/last-known result
    "invalid_plan": 3,  # the plan is wrong -> replan
}
_DEFAULT_START = 0
_GIVE_UP = {RecoveryStrategy.ESCALATE, RecoveryStrategy.TERMINATE}


@dataclass
class FailureContext:
    task_id: int
    error: str
    error_type: str
    attempts: int  # recovery attempts already made for this task


@dataclass
class RecoveryDecision:
    strategy: RecoveryStrategy
    attempt: int
    reason: str


@dataclass
class RecoveryEngine:
    max_attempts: int = 5

    def decide(self, ctx: FailureContext) -> RecoveryDecision:
        """Pick the next strategy for a failure. Always bounded → eventually gives up."""
        if ctx.attempts >= self.max_attempts:
            return RecoveryDecision(
                RecoveryStrategy.TERMINATE, ctx.attempts, "max recovery attempts reached"
            )
        start = _START_RUNG.get(ctx.error_type, _DEFAULT_START)
        rung = min(start + ctx.attempts, len(LADDER) - 1)
        strat = LADDER[rung]
        return RecoveryDecision(strat, ctx.attempts, f"{ctx.error_type}: {strat.value}")


class RecoveryExhausted(Exception):
    """Raised when the ladder reaches escalate/terminate without recovering."""

    def __init__(self, decision: RecoveryDecision, trail: list[RecoveryDecision]):
        super().__init__(f"recovery exhausted at {decision.strategy.value}")
        self.decision = decision
        self.trail = trail


Handlers = dict[RecoveryStrategy, Callable[[], Awaitable[T]]]


@dataclass
class RecoveryResult:
    value: object
    trail: list[RecoveryDecision] = field(default_factory=list)


async def execute_with_recovery(
    primary: Callable[[], Awaitable[T]],
    *,
    engine: RecoveryEngine,
    error_type: str = "error",
    handlers: Handlers | None = None,
    task_id: int = 0,
) -> RecoveryResult:
    """Run `primary`; on failure, climb the recovery ladder until it works or gives up.

    `RETRY` re-runs `primary`; other strategies dispatch to `handlers` (a strategy
    with no handler is skipped, advancing the ladder). Raises `RecoveryExhausted`
    if it reaches escalate/terminate. Returns the value plus the decision trail.
    """
    handlers = handlers or {}

    try:
        return RecoveryResult(await primary())  # happy path, no recovery needed
    except Exception as exc:  # first failure -> enter the ladder
        last_err: Exception = exc

    trail: list[RecoveryDecision] = []
    attempts = 0
    while True:
        decision = engine.decide(FailureContext(task_id, str(last_err), error_type, attempts))
        trail.append(decision)
        if decision.strategy in _GIVE_UP:
            raise RecoveryExhausted(decision, trail) from last_err

        handler = primary if decision.strategy == RecoveryStrategy.RETRY else \
            handlers.get(decision.strategy)
        if handler is None:  # nothing to run at this rung -> advance
            attempts += 1
            continue
        try:
            return RecoveryResult(await handler(), trail)
        except Exception as exc:  # this rung failed too -> climb
            last_err = exc
            attempts += 1
