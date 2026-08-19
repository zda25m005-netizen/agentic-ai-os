"""The chat-backed task executor (fake chat_fn, no network)."""
from app.missions.executor import chat_executor
from app.missions.models import Task
from app.missions.state import TaskStatus


def mk(desc: str) -> Task:
    return Task(id=1, mission_id=1, description=desc, status=TaskStatus.READY,
                depends_on=[], result=None, created_at=0.0, updated_at=0.0)


async def test_chat_executor_runs_task_through_model():
    seen = {}

    async def fake(messages):
        seen["system"] = messages[0]["content"]
        seen["user"] = messages[1]["content"]
        return "  done: baseline established  "

    execute = chat_executor(chat_fn=fake)
    result = await execute(mk("Establish baseline"))

    assert result == "done: baseline established"  # trimmed
    assert seen["user"] == "Establish baseline"
    assert "subtask" in seen["system"].lower()


async def test_chat_executor_handles_empty_reply():
    async def empty(messages):
        return ""
    result = await chat_executor(chat_fn=empty)(mk("x"))
    assert result == ""
