"""Tool registry: a typed interface for callable tools.

Each tool declares a name, a description, and a JSON-Schema for its
arguments. The registry can emit OpenAI function-calling specs (so the LLM
can pick a tool) and validate arguments before dispatching. Keeping this
strict is what stops the agent from calling tools with malformed input.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

ToolHandler = Callable[..., Awaitable[object]]


class ToolError(RuntimeError):
    """Raised for invalid tool invocations."""


class UnknownToolError(ToolError):
    """Raised when a tool name is not registered."""


@dataclass
class Tool:
    """A registered tool: metadata + async handler."""

    name: str
    description: str
    parameters: dict
    handler: ToolHandler

    def spec(self) -> dict:
        """OpenAI function-calling spec for this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class ToolRegistry:
    """Holds tools and dispatches calls to them."""

    _tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> Tool:
        if tool.name in self._tools:
            raise ToolError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise UnknownToolError(f"no such tool: {name}")
        return self._tools[name]

    def names(self) -> list[str]:
        return sorted(self._tools)

    def specs(self) -> list[dict]:
        """Function-calling specs for every registered tool."""
        return [self._tools[n].spec() for n in self.names()]

    async def execute(self, name: str, arguments: dict) -> str:
        """Validate arguments against the schema, then run the tool."""
        tool = self.get(name)
        required = tool.parameters.get("required", [])
        missing = [r for r in required if r not in arguments]
        if missing:
            raise ToolError(f"{name}: missing required args {missing}")
        from app.obs import metrics

        metrics.inc_tool(name)
        result = await tool.handler(**arguments)
        return str(result)


default_registry = ToolRegistry()


def tool(
    name: str,
    description: str,
    parameters: dict,
    registry: ToolRegistry | None = None,
) -> Callable[[ToolHandler], ToolHandler]:
    """Decorator: register an async function as a tool."""
    reg = registry or default_registry

    def decorator(fn: ToolHandler) -> ToolHandler:
        reg.register(Tool(name=name, description=description, parameters=parameters, handler=fn))
        return fn

    return decorator
