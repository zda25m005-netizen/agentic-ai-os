"""Datetime tool: give the agent the current date and time.

LLMs have no clock, so any "today", "now", or age/duration question needs
this. Returns an ISO-8601 UTC timestamp. The clock is injectable so the
tool is deterministically testable.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app.tools.registry import tool

Clock = Callable[[], datetime]


def now_iso(clock: Clock | None = None) -> str:
    """Return the current UTC time as an ISO-8601 string."""
    clock = clock or (lambda: datetime.now(UTC))
    return clock().isoformat()


@tool(
    name="current_datetime",
    description="Get the current date and time (UTC, ISO-8601).",
    parameters={"type": "object", "properties": {}, "required": []},
)
async def current_datetime() -> str:
    """Tool handler: current UTC datetime."""
    return now_iso()
