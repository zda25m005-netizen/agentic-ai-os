import pytest

from app.tools import data_analysis, file_ops, subagent
from app.tools.registry import default_registry


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(file_ops, "_workspace", lambda: tmp_path)
    return tmp_path


def test_safe_path_allows_inside(workspace):
    p = file_ops.safe_path("notes/todo.txt")
    assert str(p).startswith(str(workspace))


def test_safe_path_blocks_traversal(workspace):
    with pytest.raises(ValueError, match="escapes"):
        file_ops.safe_path("../../etc/passwd")


async def test_write_read_list_roundtrip(workspace):
    assert "wrote" in await file_ops.file_write("a.txt", "hello")
    assert await file_ops.file_read("a.txt") == "hello"
    listing = await file_ops.file_list(".")
    assert "a.txt" in listing


async def test_read_missing_file(workspace):
    out = await file_ops.file_read("nope.txt")
    assert out.startswith("error")


async def test_write_rejects_escape(workspace):
    out = await file_ops.file_write("../evil.txt", "x")
    assert out.startswith("error")


async def test_analyze_csv_operations(workspace):
    (workspace / "data.csv").write_text("name,score\nAda,90\nBo,70\n")
    assert "2 rows x 2 columns" in await data_analysis.analyze_csv("data.csv", "shape")
    assert "name" in await data_analysis.analyze_csv("data.csv", "columns")
    assert "Ada" in await data_analysis.analyze_csv("data.csv", "head")
    assert "score" in await data_analysis.analyze_csv("data.csv", "describe")


async def test_analyze_csv_missing_file(workspace):
    out = await data_analysis.analyze_csv("gone.csv")
    assert out.startswith("error")


async def test_delegate_runs_agent(monkeypatch):
    import app.agents.graph as graph_mod

    async def fake_run_agent(goal, recursion_limit=50):
        return {"answer": f"solved: {goal}"}

    monkeypatch.setattr(graph_mod, "run_agent", fake_run_agent)
    out = await subagent.delegate("find the capital of France")
    assert out == "solved: find the capital of France"


@pytest.mark.parametrize(
    "name", ["file_write", "file_read", "file_list", "analyze_csv", "delegate"]
)
def test_advanced_tools_registered(name):
    assert name in default_registry.names()
