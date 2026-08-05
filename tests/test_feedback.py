"""Feedback store + endpoint tests (in-memory SQLite; endpoint uses a fake)."""
import pytest
from fastapi.testclient import TestClient

import app.feedback.models  # noqa: F401  (registers FeedbackRow on Base)
from app.api.main import app
from app.db import session as db
from app.feedback.store import FeedbackStore

client = TestClient(app)
SQLITE_MEMORY = "sqlite+aiosqlite:///:memory:"


async def _store():
    engine = db.get_engine(SQLITE_MEMORY)
    await db.init_models(engine)
    return FeedbackStore(db.get_sessionmaker(engine)), engine


# --- store ---

async def test_save_and_recent_and_count():
    store, engine = await _store()
    await store.save("q1", "a1", "up")
    await store.save("q2", "a2", "down", better_answer="a2-better")
    assert await store.count() == 2
    recent = await store.recent()
    assert recent[0].query == "q2"
    assert recent[0].rating == "down"
    assert recent[0].better_answer == "a2-better"
    await engine.dispose()


async def test_invalid_rating_raises():
    store, engine = await _store()
    with pytest.raises(ValueError, match="rating must be"):
        await store.save("q", "a", "meh")
    await engine.dispose()


# --- endpoint (store faked) ---

def test_feedback_endpoint_records(monkeypatch):
    seen = {}

    async def fake_record(query, answer, rating, run_id=None, better_answer=None):
        seen.update(query=query, answer=answer, rating=rating,
                    run_id=run_id, better_answer=better_answer)
        return 42

    monkeypatch.setattr("app.api.main.feedback_store.record", fake_record)
    r = client.post("/feedback", json={
        "query": "capital of France?", "answer": "Paris", "rating": "up",
        "run_id": "run-1",
    })
    assert r.status_code == 200
    assert r.json() == {"id": 42, "status": "recorded"}
    assert seen["rating"] == "up" and seen["run_id"] == "run-1"


def test_feedback_endpoint_rejects_bad_rating():
    r = client.post("/feedback", json={"query": "q", "answer": "a", "rating": "sideways"})
    assert r.status_code == 422
