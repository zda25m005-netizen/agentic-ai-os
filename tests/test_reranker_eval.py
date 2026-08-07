"""Feedback-loop evaluation tests (offline, no embeddings/LLM)."""
from fastapi.testclient import TestClient

from app.api.main import app
from app.rag.vectorstore import SearchHit
from eval import reranker_eval

client = TestClient(app)


def _hit(source, text=""):
    return SearchHit(id=source, score=0.0, payload={"source": source, "text": text})


async def test_rerank_recall_improves_with_good_reranker():
    # Gold source "A" starts at rank 2 (out of top_k=1 window it's missed).
    candidates = [_hit("B"), _hit("A")]
    items = [("q", candidates, "A")]

    async def identity(_q, hits):
        return hits

    async def move_gold_first(_q, hits):
        return sorted(hits, key=lambda h: h.payload["source"] != "A")

    off = await reranker_eval.rerank_recall_on_candidates(items, identity, top_k=1)
    on = await reranker_eval.rerank_recall_on_candidates(items, move_gold_first, top_k=1)
    assert off == 0.0 and on == 1.0


async def test_compare_on_candidates_returns_named_scores():
    items = [("q", [_hit("A")], "A")]

    async def identity(_q, hits):
        return hits

    results = await reranker_eval.compare_on_candidates(items, {"off": identity}, top_k=1)
    assert results == {"off": 1.0}


def test_format_comparison_table():
    table = reranker_eval.format_comparison({"LLM reranker": 1.0, "feedback reranker": 0.5})
    assert "| LLM reranker | 100% |" in table
    assert "| feedback reranker | 50% |" in table


def test_ablation_supports_feedback_label():
    from eval.ablation import format_ablation_table
    results = {1: {"vector": 0.5, "bm25": 0.5, "hybrid": 1.0, "feedback": 1.0}}
    table = format_ablation_table(results)
    assert "Hybrid + feedback reranker" in table


# --- /admin/stats feedback metrics ---

def _admin_token():
    r = client.post("/token", json={"username": "admin", "password": "admin123"})
    return r.json()["access_token"]


def test_admin_stats_includes_feedback(monkeypatch):
    async def fake_summary():
        return {"total": 3, "up": 2, "down": 1, "with_better_answer": 1}

    monkeypatch.setattr("app.api.main.feedback_store.summary", fake_summary)
    r = client.get("/admin/stats", headers={"Authorization": f"Bearer {_admin_token()}"})
    assert r.status_code == 200
    body = r.json()
    assert body["viewer"] == "admin"
    assert body["feedback"] == {"total": 3, "up": 2, "down": 1, "with_better_answer": 1}
