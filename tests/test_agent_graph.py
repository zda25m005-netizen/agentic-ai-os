import app.core.llm as llm_mod
from app.agents.graph import build_graph, finalize_node
from app.agents.state import new_state


def test_new_state_defaults():
    s = new_state("summarize the report")
    assert s["goal"] == "summarize the report"
    assert s["plan"] == []
    assert s["cursor"] == 0
    assert s["retries"] == 0
    assert s["verdict"] is None


def test_finalize_joins_results():
    state = new_state("goal")
    state["results"] = ["first", "second"]
    update = finalize_node(state)
    assert update["answer"] == "first\n\nsecond"
    assert any(m["node"] == "finalize" for m in update["scratchpad"])


def _router_chat_raw(approve: bool = True):
    async def fake(messages, tools=None, temperature=0.2):
        system = messages[0]["content"].lower()
        if "planning agent" in system:
            return {"content": '[{"description": "step A", "agent": "research"}, '
                               '{"description": "step B", "agent": "coding"}]'}
        if "reviewer" in system:
            return {"content": "APPROVE" if approve else "RETRY: not good enough"}
        return {"content": "worker result"}

    return fake


async def test_full_graph_runs_end_to_end(monkeypatch):
    monkeypatch.setattr(llm_mod, "chat_raw", _router_chat_raw(approve=True))
    graph = build_graph()

    result = await graph.ainvoke(new_state("do the task"))

    assert len(result["plan"]) == 2
    assert result["cursor"] == 2
    assert result["results"] == ["worker result", "worker result"]
    assert result["answer"] == "worker result\n\nworker result"
    nodes = {m["node"] for m in result["scratchpad"]}
    assert {"planner", "executor", "critic", "finalize"}.issubset(nodes)


async def test_graph_retries_then_finishes(monkeypatch):
    monkeypatch.setattr(llm_mod, "chat_raw", _router_chat_raw(approve=False))
    graph = build_graph()

    result = await graph.ainvoke(new_state("do the task"))

    assert "answer" in result
    assert any(m["node"] == "finalize" for m in result["scratchpad"])
    assert any("retry" in m["content"] for m in result["scratchpad"])
