from fastapi.testclient import TestClient

import app.core.llm as llm_mod
from app.api.main import app

client = TestClient(app)


def test_agent_requires_config(monkeypatch):
    monkeypatch.setattr(llm_mod, "is_configured", lambda: False)
    r = client.post("/agent", json={"goal": "do it"})
    assert r.status_code == 503


def test_agent_runs_and_returns_plan(monkeypatch):
    monkeypatch.setattr(llm_mod, "is_configured", lambda: True)

    async def fake_chat(messages):
        system = messages[0]["content"].lower()
        if "planning agent" in system:
            return '[{"description": "gather facts", "agent": "research"}]'
        if "reviewer" in system:
            return "APPROVE"
        return "the worker did the thing"

    monkeypatch.setattr(llm_mod, "chat", fake_chat)

    r = client.post("/agent", json={"goal": "summarize the report"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "the worker did the thing"
    assert body["steps"][0]["description"] == "gather facts"
    assert body["steps"][0]["status"] == "done"
    assert any("planner" in line for line in body["trace"])
    assert any("finalize" in line for line in body["trace"])
