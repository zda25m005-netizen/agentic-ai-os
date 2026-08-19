"""The pluggable unit of work: how a single task gets executed.

The runtime doesn't know *how* a task runs — it just calls a `TaskExecutor`.
That keeps the DAG-driving loop (runtime.py) independent of the agent stack, so
tests inject a fake executor and later days can swap in the tool-using agent
without touching the runtime.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.core import llm
from app.missions.models import Task

# Given a task, do the work and return a concise result. Raising signals failure.
TaskExecutor = Callable[[Task], Awaitable[str]]

ChatFn = Callable[[list[dict]], Awaitable[str]]

_SYSTEM = (
    "You are an autonomous agent executing ONE subtask of a larger mission. "
    "Carry out the task and return a concise result — findings, output, or a "
    "short summary of what you did. Plain text only."
)


def chat_executor(chat_fn: ChatFn | None = None) -> TaskExecutor:
    """A `TaskExecutor` that runs each task through the chat model.

    A stopgap execution unit (single LLM call). The full tool-using agent plugs
    in here later; the runtime contract is unchanged.
    """
    chat = chat_fn or llm.chat

    async def execute(task: Task) -> str:
        raw = await chat([
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": task.description},
        ])
        return (raw or "").strip()

    return execute
