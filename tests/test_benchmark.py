"""Fault-injection benchmark: task generation, harness, metrics, determinism."""
from benchmarks.harness import _is_unsafe, _select_tool, run_benchmark
from benchmarks.metrics import aggregate
from benchmarks.tasks import CATEGORIES, generate_tasks


def test_generate_tasks_covers_all_categories():
    tasks = generate_tasks(per_category=4)
    assert len(tasks) == 4 * len(CATEGORIES)
    assert {t.category for t in tasks} == set(CATEGORIES)


def test_tool_selector_routes_by_keyword():
    assert _select_tool("calculate the total") == "calculator"
    assert _select_tool("query the database") == "sql_tool"
    assert _select_tool("recall the value") == "rag_search"
    assert _select_tool("handle case 3") == "web_search"  # no keyword -> default


def test_safety_flags_unsafe_goals():
    assert _is_unsafe("delete all records for user 1")
    assert not _is_unsafe("search the web for topic 1")


async def test_benchmark_produces_real_metrics():
    results = await run_benchmark(per_category=5, seed=42)
    m = aggregate(results)
    assert m["n_tasks"] == 5 * len(CATEGORIES)
    # every metric present and in range
    for key in ("task_success_rate", "recovery_rate", "tool_selection_accuracy",
                "memory_retrieval_rate", "safety_block_rate", "planning_validity",
                "human_intervention_rate"):
        assert 0.0 <= m[key] <= 1.0


async def test_benchmark_expected_behaviors():
    m = aggregate(await run_benchmark(per_category=5, seed=42))
    # honest, expected outcomes of the fault model
    assert m["success_by_category"]["easy"] == 1.0
    assert m["success_by_category"]["hard"] == 0.0        # double fault escalates
    assert m["memory_retrieval_rate"] == 1.0              # seeded facts recalled
    assert m["safety_block_rate"] == 1.0                  # unsafe goals blocked
    assert m["recovery_rate"] == round(2 / 3, 4)          # 2 of 3 fault categories recover


async def test_benchmark_is_reproducible():
    a = aggregate(await run_benchmark(per_category=5, seed=42))
    b = aggregate(await run_benchmark(per_category=5, seed=42))
    assert a["success_by_category"] == b["success_by_category"]
    assert a["task_success_rate"] == b["task_success_rate"]
    assert a["recovery_rate"] == b["recovery_rate"]
