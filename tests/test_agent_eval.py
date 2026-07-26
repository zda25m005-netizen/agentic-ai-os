from app.agents.state import Step, new_state
from eval import agent_eval
from eval.agent_eval import AgentTask


def _state(answer: str, statuses: list[str]) -> dict:
    s = new_state("goal")
    s["answer"] = answer
    s["plan"] = [
        Step(id=i, description=f"step {i}", agent="research", status=st)
        for i, st in enumerate(statuses)
    ]
    return s


def test_tasks_load_and_are_well_formed():
    tasks = agent_eval.load_tasks()
    assert len(tasks) >= 5
    assert all(t.goal and t.expected_keywords for t in tasks)


def test_score_task_success():
    task = AgentTask("t", "goal", ["paris"], min_steps=1)
    row = agent_eval.score_task(task, _state("The capital is Paris.", ["done"]))
    assert row["success"] == 1.0
    assert row["completed"] == 1.0
    assert row["steps"] == 1


def test_score_task_missing_keyword_fails():
    task = AgentTask("t", "goal", ["tokyo"], min_steps=1)
    row = agent_eval.score_task(task, _state("The capital is Paris.", ["done"]))
    assert row["success"] == 0.0


def test_score_task_incomplete_steps():
    task = AgentTask("t", "goal", ["paris"], min_steps=1)
    row = agent_eval.score_task(task, _state("Paris.", ["done", "pending"]))
    assert row["completed"] == 0.0


def test_score_task_too_few_steps():
    task = AgentTask("t", "goal", ["paris"], min_steps=3)
    row = agent_eval.score_task(task, _state("Paris.", ["done"]))
    assert row["success"] == 0.0


async def test_run_agent_eval_aggregates():
    tasks = [
        AgentTask("a", "capital of france", ["paris"], 1),
        AgentTask("b", "capital of japan", ["tokyo"], 1),
    ]

    async def fake_run(goal):
        if "france" in goal:
            return _state("It is Paris.", ["done"])
        return _state("Not sure.", ["done"])

    report = await agent_eval.run_agent_eval(tasks, fake_run)
    assert report.n == 2
    assert report.task_success == 0.5
    assert report.completion_rate == 1.0


def test_format_report_md():
    report = agent_eval.AgentEvalReport(
        n=5, task_success=0.8, completion_rate=1.0, avg_steps=2.4
    )
    md = agent_eval.format_report_md(report)
    assert "Task success rate" in md
    assert "80%" in md
