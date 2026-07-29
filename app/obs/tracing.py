"""Lightweight tracing: span timings + token/cost accounting.

A `Trace` collects spans (named, timed, with metadata) for one request. The
current trace lives in a contextvar so instrumented calls (LLM, tools) can
record into it without being passed a handle — and it's a no-op when no
trace is active, so nothing is forced to run under tracing.

Token usage and an estimated USD cost are aggregated from LLM spans, giving
the per-request latency and cost numbers a production system needs.
"""
from __future__ import annotations

import contextvars
import time
from collections.abc import Awaitable
from dataclasses import dataclass, field
from typing import TypeVar

T = TypeVar("T")

# USD per 1M tokens (input, output). Extend as models are added.
_PRICES = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimated USD cost for a call, 0.0 if the model price is unknown."""
    inp, out = _PRICES.get(model, (0.0, 0.0))
    return (prompt_tokens * inp + completion_tokens * out) / 1_000_000


@dataclass
class Span:
    name: str
    duration_ms: float
    metadata: dict = field(default_factory=dict)


@dataclass
class Trace:
    spans: list[Span] = field(default_factory=list)

    def add(self, span: Span) -> None:
        self.spans.append(span)

    def summary(self) -> dict:
        total_ms = sum(s.duration_ms for s in self.spans)
        prompt = sum(s.metadata.get("prompt_tokens", 0) for s in self.spans)
        completion = sum(s.metadata.get("completion_tokens", 0) for s in self.spans)
        cost = sum(
            estimate_cost(
                s.metadata.get("model", ""),
                s.metadata.get("prompt_tokens", 0),
                s.metadata.get("completion_tokens", 0),
            )
            for s in self.spans
        )
        by_name: dict[str, int] = {}
        for s in self.spans:
            by_name[s.name] = by_name.get(s.name, 0) + 1
        return {
            "spans": len(self.spans),
            "total_ms": round(total_ms, 2),
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "est_cost_usd": round(cost, 6),
            "by_name": by_name,
        }


_current: contextvars.ContextVar[Trace | None] = contextvars.ContextVar(
    "current_trace", default=None
)


def start_trace() -> Trace:
    """Begin a new trace and make it current."""
    trace = Trace()
    _current.set(trace)
    return trace


def current_trace() -> Trace | None:
    return _current.get()


def clear_trace() -> None:
    _current.set(None)


def record_span(name: str, duration_ms: float, **metadata: object) -> None:
    """Add a span to the current trace (no-op if none is active)."""
    trace = _current.get()
    if trace is not None:
        trace.add(Span(name=name, duration_ms=duration_ms, metadata=dict(metadata)))


async def traced(name: str, awaitable: Awaitable[T], **metadata: object) -> T:
    """Await `awaitable`, timing it and recording a span."""
    t0 = time.perf_counter()
    try:
        return await awaitable
    finally:
        record_span(name, (time.perf_counter() - t0) * 1000.0, **metadata)
