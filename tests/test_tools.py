import pytest

from app.tools import calculator as calc_mod
from app.tools.registry import (
    Tool,
    ToolError,
    ToolRegistry,
    UnknownToolError,
    tool,
)


def _echo_tool(reg: ToolRegistry):
    @tool(
        name="echo",
        description="Echo the input.",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        registry=reg,
    )
    async def echo(text: str) -> str:
        return text


async def test_register_get_and_names():
    reg = ToolRegistry()
    _echo_tool(reg)
    assert reg.names() == ["echo"]
    assert isinstance(reg.get("echo"), Tool)


async def test_specs_are_function_calling_format():
    reg = ToolRegistry()
    _echo_tool(reg)
    spec = reg.specs()[0]
    assert spec["type"] == "function"
    assert spec["function"]["name"] == "echo"
    assert "text" in spec["function"]["parameters"]["properties"]


async def test_execute_runs_handler():
    reg = ToolRegistry()
    _echo_tool(reg)
    out = await reg.execute("echo", {"text": "hello"})
    assert out == "hello"


async def test_execute_unknown_tool_raises():
    reg = ToolRegistry()
    with pytest.raises(UnknownToolError):
        await reg.execute("nope", {})


async def test_execute_missing_required_arg_raises():
    reg = ToolRegistry()
    _echo_tool(reg)
    with pytest.raises(ToolError, match="missing required"):
        await reg.execute("echo", {})


async def test_double_register_raises():
    reg = ToolRegistry()
    _echo_tool(reg)
    with pytest.raises(ToolError, match="already registered"):
        _echo_tool(reg)


def test_calculator_safe_eval():
    assert calc_mod.safe_eval("2 + 2 * 3") == 8
    assert calc_mod.safe_eval("(1 + 2) ** 3") == 27
    assert calc_mod.safe_eval("-5 + 10") == 5


def test_calculator_rejects_code():
    with pytest.raises(ValueError):
        calc_mod.safe_eval("__import__('os').system('ls')")


async def test_calculator_handler_computes():
    assert await calc_mod.calculator("10 / 4") == "2.5"


async def test_calculator_handler_reports_error():
    out = await calc_mod.calculator("2 +")
    assert out.startswith("error")
