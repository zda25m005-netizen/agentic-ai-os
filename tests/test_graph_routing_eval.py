"""Tests for relational routing and the GraphRAG eval harness."""
from app.agents import planner
from app.graph import routing
from eval import graph_eval

# --- routing heuristic ---

def test_is_relational_goal_detects_relationships():
    assert routing.is_relational_goal("How is Acme connected to SKU-4471?")
    assert routing.is_relational_goal("What is the relationship between A and B?")
    assert routing.is_relational_goal("Who does Alice report to?")


def test_is_relational_goal_false_for_plain_lookup():
    assert not routing.is_relational_goal("How many leave days do employees get?")
    assert not routing.is_relational_goal("Summarize the Q3 report")


# --- planner injects the graph hint ---

async def test_plan_goal_injects_graph_hint():
    captured = {}

    async def fake_chat(messages):
        captured["user"] = messages[-1]["content"]
        return '[{"description": "use graph_search", "agent": "research"}]'

    await planner.plan_goal("q?", chat_fn=fake_chat, extra_hint=routing.GRAPH_HINT)
    assert "graph_search" in captured["user"]
    assert routing.GRAPH_HINT in captured["user"]


async def test_plan_goal_no_hint_when_absent():
    captured = {}

    async def fake_chat(messages):
        captured["user"] = messages[-1]["content"]
        return '[{"description": "step", "agent": "research"}]'

    await planner.plan_goal("q?", chat_fn=fake_chat)
    assert routing.GRAPH_HINT not in captured["user"]


# --- eval scorer + runner ---

def test_fact_coverage_partial_and_full():
    assert graph_eval.fact_coverage("shipped SKU-4471 to Berlin", ["SKU-4471", "Berlin"]) == 1.0
    assert graph_eval.fact_coverage("shipped SKU-4471", ["SKU-4471", "Berlin"]) == 0.5
    assert graph_eval.fact_coverage("nothing", ["X"]) == 0.0


def test_dataset_loads_and_is_nonempty():
    items = graph_eval.load_graph_qa()
    assert len(items) >= 5
    assert all("question" in it and "expected_facts" in it for it in items)


async def test_run_graph_eval_scores_all_items():
    items = [
        {"id": "a", "question": "q1", "expected_facts": ["paris"]},
        {"id": "b", "question": "q2", "expected_facts": ["london"]},
    ]

    async def answer_fn(_q):
        return "The answer mentions paris only."

    report = await graph_eval.run_graph_eval(answer_fn, items=items)
    assert report.n == 2
    assert report.coverage == 0.5  # 1.0 for 'paris', 0.0 for 'london'
    assert {r["id"] for r in report.per_item} == {"a", "b"}
