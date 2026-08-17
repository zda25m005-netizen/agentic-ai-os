"""End-to-end smoke: walk the whole API surface in one offline journey.

Health -> readiness -> config -> auth (login/me) -> RAG /ask -> multi-agent
/agent -> /feedback -> /metrics. Everything is monkeypatched to run without a
network, an LLM, or live datastores — a fast capstone that proves the wiring.
"""
from fastapi.testclient import TestClient

from app.api.main import app
from app.core import llm
from app.rag import retriever, vectorstore
from app.rag.vectorstore import SearchHit

client = TestClient(app)


def test_full_user_journey(monkeypatch):
    # --- ops endpoints ---
    assert client.get("/health").json()["status"] == "ok"
    ready = client.get("/readyz")
    assert ready.status_code == 200 and "deps" in ready.json()
    assert "active_model" in client.get("/config").json()

    # --- auth: login -> me ---
    tok = client.post("/token", json={"username": "user", "password": "user123"})
    access = tok.json()["access_token"]
    me = client.get("/me", headers={"Authorization": f"Bearer {access}"})
    assert me.json() == {"username": "user", "role": "user"}

    # --- RAG /ask (vector, offline) ---
    monkeypatch.setattr(llm, "is_configured", lambda: True)
    monkeypatch.setattr(vectorstore, "get_client", lambda *a, **k: object())

    async def fake_retrieve(q, c, collection="documents", limit=5):
        return [SearchHit(id="1", score=0.9,
                          payload={"text": "The capital is Paris.",
                                   "source": "geo.pdf", "chunk_index": 0})]

    async def fake_chat(messages, temperature=0.2):
        return "The capital is Paris [1]."

    monkeypatch.setattr(retriever, "retrieve", fake_retrieve)
    monkeypatch.setattr(llm, "chat", fake_chat)
    ask = client.post("/ask", json={"question": "capital of France?"})
    assert "Paris" in ask.json()["answer"]
    assert ask.json()["sources"][0]["source"] == "geo.pdf"

    # --- multi-agent /agent (offline via fake run) ---
    async def fake_run_agent(goal, recursion_limit=50):
        return {
            "goal": goal,
            "plan": [{"id": 0, "description": "do it", "agent": "research", "status": "done"}],
            "scratchpad": [{"node": "planner", "content": "planned 1 step(s)"}],
            "answer": "done",
        }

    monkeypatch.setattr("app.api.main.run_agent", fake_run_agent)
    agent = client.post("/agent", json={"goal": "anything"})
    body = agent.json()
    assert agent.status_code == 200 and body["answer"] == "done"
    assert body["steps"][0]["agent"] == "research"
    assert "metrics" in body

    # --- feedback (offline store) ---
    async def fake_record(query, answer, rating, run_id=None, better_answer=None):
        return 7

    monkeypatch.setattr("app.api.main.feedback_store.record", fake_record)
    fb = client.post("/feedback", json={"query": "q", "answer": "a", "rating": "up"})
    assert fb.json() == {"id": 7, "status": "recorded"}

    # --- metrics reflect all the traffic ---
    metrics = client.get("/metrics").text
    assert "agentic_requests_total" in metrics
    assert 'endpoint="/agent"' in metrics
