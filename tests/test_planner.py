from app.agents import planner
from app.agents.state import new_state


def test_parse_plan_valid_json():
    raw = '[{"description": "search docs", "agent": "research"}, ' \
          '{"description": "write code", "agent": "coding"}]'
    steps = planner.parse_plan(raw, "goal")
    assert [s["description"] for s in steps] == ["search docs", "write code"]
    assert [s["agent"] for s in steps] == ["research", "coding"]
    assert all(s["status"] == "pending" for s in steps)
    assert [s["id"] for s in steps] == [0, 1]


def test_parse_plan_coerces_unknown_agent():
    raw = '[{"description": "do a thing", "agent": "wizard"}]'
    steps = planner.parse_plan(raw, "goal")
    assert steps[0]["agent"] == "research"


def test_parse_plan_extracts_array_from_prose():
    raw = 'Here is your plan:\n[{"description": "x", "agent": "sql"}]\nThanks!'
    steps = planner.parse_plan(raw, "goal")
    assert steps[0]["agent"] == "sql"


def test_parse_plan_falls_back_on_garbage():
    steps = planner.parse_plan("not json at all", "summarize the report")
    assert len(steps) == 1
    assert steps[0]["description"] == "summarize the report"
    assert steps[0]["agent"] == "research"


async def test_plan_goal_uses_chat_fn():
    async def fake_chat(messages):
        return '[{"description": "step one", "agent": "research"}]'

    steps = await planner.plan_goal("do it", chat_fn=fake_chat)
    assert steps[0]["description"] == "step one"


async def test_planner_node_updates_state():
    async def fake_chat(messages):
        return '[{"description": "a", "agent": "research"}, ' \
               '{"description": "b", "agent": "coding"}]'

    import app.core.llm as llm_mod
    orig = llm_mod.chat
    llm_mod.chat = fake_chat
    try:
        state = new_state("some goal")
        update = await planner.planner_node(state)
    finally:
        llm_mod.chat = orig

    assert len(update["plan"]) == 2
    assert update["cursor"] == 0
    assert any(m["node"] == "planner" for m in update["scratchpad"])
