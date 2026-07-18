from fastapi.testclient import TestClient

from app.api.main import app
from app.core import llm

client = TestClient(app)


def test_chat_requires_config(monkeypatch):
    # Force "not configured" so the test is deterministic in CI.
    monkeypatch.setattr(llm, "is_configured", lambda: False)
    r = client.post("/chat", json={"message": "hello"})
    assert r.status_code == 503


def test_chat_success(monkeypatch):
    async def fake_chat(messages, temperature=0.2):
        return "pong"

    monkeypatch.setattr(llm, "is_configured", lambda: True)
    monkeypatch.setattr(llm, "chat", fake_chat)

    r = client.post("/chat", json={"message": "ping"})
    assert r.status_code == 200
    assert r.json()["reply"] == "pong"
