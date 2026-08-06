"""Feedback-driven reranker tests (deterministic, no model/API)."""
from dataclasses import dataclass

from app.rag import feedback_reranker as fr
from app.rag.vectorstore import SearchHit


def _hit(text, id="x"):
    return SearchHit(id=id, score=0.0, payload={"text": text})


# --- features ---

def test_features_reward_overlap():
    cov, jac, length = fr.features("alpha beta", "alpha beta gamma")
    assert cov == 1.0  # both query terms present
    assert 0.0 < jac <= 1.0
    assert fr.features("alpha beta", "zzz")[0] == 0.0


# --- learning + ordering ---

def _training_pairs():
    pairs = []
    for q, good, bad in [
        ("alpha beta", "alpha beta gamma delta", "zzz nothing here"),
        ("cat dog", "cat dog bird fish", "quantum tunnel"),
        ("red blue", "red blue green", "totally unrelated"),
    ]:
        pairs.append(fr.TrainingPair(q, good, 1))
        pairs.append(fr.TrainingPair(q, bad, 0))
    return pairs


def test_fit_learns_to_rank_relevant_first():
    model = fr.LearnedReranker(min_pairs=4).fit(_training_pairs())
    assert model.is_fitted
    assert model.score("alpha beta", "alpha beta gamma") > model.score("alpha beta", "zzz")


async def test_rerank_orders_by_learned_score():
    model = fr.LearnedReranker(min_pairs=4).fit(_training_pairs())
    hits = [_hit("totally unrelated text", "low"), _hit("alpha beta present", "high")]
    ranked = await model.rerank("alpha beta", hits)
    assert ranked[0].id == "high"


# --- cold-start fallback ---

async def test_cold_start_falls_back_to_llm_reranker():
    model = fr.LearnedReranker(min_pairs=4)  # never fitted
    assert not model.is_fitted
    hits = [_hit("passage zero", "0"), _hit("passage one", "1")]

    async def fake_chat(messages):
        return '{"0": 1, "1": 9}'  # LLM says index 1 is far more relevant

    ranked = await model.rerank("q", hits, chat_fn=fake_chat)
    assert ranked[0].id == "1"


def test_fit_stays_cold_with_too_few_pairs():
    model = fr.LearnedReranker(min_pairs=4)
    model.fit([fr.TrainingPair("q", "p", 1), fr.TrainingPair("q", "p2", 0)])
    assert not model.is_fitted  # below min_pairs -> stays cold


# --- pair collection from feedback ---

@dataclass
class _FB:
    query: str
    rating: str


async def test_pairs_from_feedback_labels_by_rating():
    feedback = [_FB("good query", "up"), _FB("bad query", "down")]

    async def fake_retrieve(query):
        return [_hit(f"passage for {query}")]

    pairs = await fr.pairs_from_feedback(feedback, fake_retrieve)
    labels = {p.query: p.label for p in pairs}
    assert labels == {"good query": 1, "bad query": 0}
