from app.agents.graph import build_graph
from app.agents.state import new_state


def test_new_state_defaults():
    s = new_state("summarize the report")
    assert s["goal"] == "summarize the report"
    assert s["plan"] == []
    assert s["cursor"] == 0
    assert s["retries"] == 0
    assert s["verdict"] is None


def test_graph_compiles_and_runs():
    graph = build_graph()
    result = graph.invoke(new_state("test goal"))
    assert result["goal"] == "test goal"
    assert any(m["node"] == "start" for m in result["scratchpad"])
    assert "test goal" in result["scratchpad"][-1]["content"]


def test_graph_is_deterministic_shape():
    graph = build_graph()
    r1 = graph.invoke(new_state("a"))
    r2 = graph.invoke(new_state("b"))
    assert set(r1).issuperset({"goal", "scratchpad"})
    assert r1["goal"] == "a"
    assert r2["goal"] == "b"
