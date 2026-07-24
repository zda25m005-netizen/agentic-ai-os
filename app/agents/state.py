"""Shared state for the multi-agent graph.

Every node in the LangGraph flow reads and writes this typed state. Keeping
it in one place means the Planner, workers, and Critic all agree on the
shape of a task as it moves through the system.
"""
from __future__ import annotations

from typing import Literal, TypedDict

Verdict = Literal["retry", "done"]
StepStatus = Literal["pending", "in_progress", "done", "failed"]


class Step(TypedDict, total=False):
    """One unit of work in a plan."""

    id: int
    description: str
    agent: str
    status: StepStatus
    result: str


class Message(TypedDict):
    """A scratchpad entry recording what a node did."""

    node: str
    content: str


class AgentState(TypedDict, total=False):
    """State threaded through the entire agent graph."""

    goal: str
    plan: list[Step]
    cursor: int
    scratchpad: list[Message]
    results: list[str]
    verdict: Verdict | None
    retries: int
    answer: str
    cost_tokens: int


def new_state(goal: str) -> AgentState:
    """Create a fresh state for a goal with sensible defaults."""
    return AgentState(
        goal=goal,
        plan=[],
        cursor=0,
        scratchpad=[],
        results=[],
        verdict=None,
        retries=0,
        answer="",
        cost_tokens=0,
    )
