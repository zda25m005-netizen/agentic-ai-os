from app.agents.tool_loop import run_with_tools
from app.tools.registry import ToolRegistry, tool


def _calc_registry() -> ToolRegistry:
    reg = ToolRegistry()

    @tool(
        name="calculator",
        description="Add numbers.",
        parameters={
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
        registry=reg,
    )
    async def calc(expression: str) -> str:
        return "8"

    return reg


async def test_returns_text_when_no_tool_calls():
    async def chat_raw(messages, tools=None, temperature=0.2):
        return {"content": "final answer"}

    out = await run_with_tools([{"role": "user", "content": "hi"}],
                               registry=ToolRegistry(), chat_raw=chat_raw)
    assert out == "final answer"


async def test_executes_tool_then_answers():
    reg = _calc_registry()
    turns = {"n": 0}

    async def chat_raw(messages, tools=None, temperature=0.2):
        turns["n"] += 1
        if turns["n"] == 1:
            return {"tool_calls": [{"id": "c1", "function": {
                "name": "calculator", "arguments": '{"expression": "2+2*3"}'}}]}
        assert any(m.get("role") == "tool" for m in messages)
        return {"content": "the answer is 8"}

    out = await run_with_tools([{"role": "user", "content": "compute 2+2*3"}],
                               registry=reg, chat_raw=chat_raw)
    assert "8" in out
    assert turns["n"] == 2


async def test_unknown_tool_does_not_crash():
    async def chat_raw(messages, tools=None, temperature=0.2):
        if not any(m.get("role") == "tool" for m in messages):
            return {"tool_calls": [{"id": "c1", "function": {
                "name": "does_not_exist", "arguments": "{}"}}]}
        return {"content": "recovered"}

    out = await run_with_tools([{"role": "user", "content": "x"}],
                               registry=ToolRegistry(), chat_raw=chat_raw)
    assert out == "recovered"


async def test_max_iters_forces_final_answer():
    async def chat_raw(messages, tools=None, temperature=0.2):
        if tools is not None:
            return {"tool_calls": [{"id": "c", "function": {
                "name": "x", "arguments": "{}"}}]}
        return {"content": "forced final"}

    out = await run_with_tools([{"role": "user", "content": "x"}],
                               registry=ToolRegistry(), chat_raw=chat_raw, max_iters=2)
    assert out == "forced final"
