from app.agents import executor
from app.agents.state import Step, new_state


def _state_with_plan() -> dict:
    state = new_state("goal")
    state["plan"] = [
        Step(id=0, description="find revenue", agent="research", status="pending"),
        Step(id=1, description="compute growth", agent="coding", status="pending"),
    ]
    return state


def test_is_done():
    s = _state_with_plan()
    assert executor.is_done(s) is False
    s["cursor"] = 2
    assert executor.is_done(s) is True


async def test_execute_step_uses_agent_prompt():
    captured = {}

    async def fake_chat(messages):
        captured["system"] = messages[0]["content"]
        return "result text"

    step = Step(id=0, description="do sql", agent="sql", status="pending")
    out = await executor.execute_step(step, chat_fn=fake_chat)
    assert out == "result text"
    assert "data agent" in captured["system"]


def _patch_chat(fake):
    import app.core.llm as llm_mod
    orig = llm_mod.chat
    llm_mod.chat = fake
    return llm_mod, orig


async def test_executor_node_runs_current_step_and_advances():
    async def fake_chat(messages):
        return "step result"

    llm_mod, orig = _patch_chat(fake_chat)
    try:
        update = await executor.executor_node(_state_with_plan())
    finally:
        llm_mod.chat = orig

    assert update["cursor"] == 1
    assert update["results"] == ["step result"]
    assert update["plan"][0]["status"] == "done"
    assert update["plan"][0]["result"] == "step result"
    assert update["plan"][1]["status"] == "pending"


async def test_executor_node_noop_when_cursor_past_end():
    s = _state_with_plan()
    s["cursor"] = 2
    update = await executor.executor_node(s)
    assert update == {}


async def test_executor_walks_all_steps():
    async def fake_chat(messages):
        return "ok"

    llm_mod, orig = _patch_chat(fake_chat)
    try:
        state = _state_with_plan()
        for _ in range(len(state["plan"])):
            update = await executor.executor_node(state)
            state.update(update)
    finally:
        llm_mod.chat = orig

    assert state["cursor"] == 2
    assert len(state["results"]) == 2
    assert all(s["status"] == "done" for s in state["plan"])
