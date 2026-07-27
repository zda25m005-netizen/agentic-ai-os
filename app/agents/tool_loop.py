"""The tool-use loop: let the LLM call tools until it produces an answer.

This is the core of function-calling. Each turn:
  1. send the conversation + tool specs to the LLM
  2. if it asks to call tools, execute each via the registry and append the
     results as `tool` messages
  3. repeat until the LLM answers with plain text (no tool calls)

A hard iteration cap bounds cost and prevents infinite tool loops; if hit,
one final tool-free turn forces a text answer.
"""
from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from app.core import llm
from app.tools.registry import ToolError, ToolRegistry, default_registry

MAX_TOOL_ITERS = 5

ChatRawFn = Callable[..., Awaitable[dict]]


async def _run_tool_calls(tool_calls: list[dict], registry: ToolRegistry) -> list[dict]:
    """Execute each requested tool call; return `tool` result messages."""
    messages: list[dict] = []
    for call in tool_calls:
        fn = call.get("function", {})
        name = fn.get("name", "")
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {}
        try:
            result = await registry.execute(name, args)
        except ToolError as exc:
            result = f"error: {exc}"
        except Exception as exc:  # noqa: BLE001 - never let a tool crash the loop
            result = f"error: tool '{name}' raised: {exc}"
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "name": name,
                "content": result,
            }
        )
    return messages


async def run_with_tools(
    messages: list[dict],
    registry: ToolRegistry | None = None,
    chat_raw: ChatRawFn | None = None,
    max_iters: int = MAX_TOOL_ITERS,
) -> str:
    """Drive the LLM <-> tools loop and return the final text answer."""
    registry = registry or default_registry
    chat_raw = chat_raw or llm.chat_raw
    specs = registry.specs()

    for _ in range(max_iters):
        message = await chat_raw(messages, tools=specs)
        tool_calls = message.get("tool_calls")
        if not tool_calls:
            return message.get("content") or ""
        messages.append(message)
        messages.extend(await _run_tool_calls(tool_calls, registry))

    final = await chat_raw(messages, tools=None)
    return final.get("content") or ""
