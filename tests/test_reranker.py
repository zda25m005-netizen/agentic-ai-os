from app.rag import reranker
from app.rag.vectorstore import SearchHit


def _hits(n: int) -> list[SearchHit]:
    return [SearchHit(id=str(i), score=1.0, payload={"text": f"passage {i}"})
            for i in range(n)]


def test_parse_scores_valid():
    assert reranker.parse_scores('{"0": 8, "1": 2}', 2) == {0: 8.0, 1: 2.0}


def test_parse_scores_extracts_from_prose():
    assert reranker.parse_scores('scores: {"0": 5}. done', 1) == {0: 5.0}


def test_parse_scores_drops_out_of_range_and_bad():
    assert reranker.parse_scores('{"0": 9, "5": 1, "x": 3}', 2) == {0: 9.0}


def test_parse_scores_garbage_returns_empty():
    assert reranker.parse_scores("not json", 3) == {}


async def test_rerank_reorders_by_score():
    async def fake_chat(messages):
        return '{"0": 2, "1": 9, "2": 5}'

    hits = _hits(3)
    ranked = await reranker.rerank("q", hits, chat_fn=fake_chat)
    assert [h.id for h in ranked] == ["1", "2", "0"]


async def test_rerank_top_k():
    async def fake_chat(messages):
        return '{"0": 2, "1": 9, "2": 5}'

    ranked = await reranker.rerank("q", _hits(3), chat_fn=fake_chat, top_k=2)
    assert [h.id for h in ranked] == ["1", "2"]


async def test_rerank_empty():
    async def fake_chat(messages):
        return "{}"

    assert await reranker.rerank("q", [], chat_fn=fake_chat) == []


async def test_rerank_bad_json_keeps_order():
    async def fake_chat(messages):
        return "sorry, no scores"

    hits = _hits(3)
    ranked = await reranker.rerank("q", hits, chat_fn=fake_chat)
    assert [h.id for h in ranked] == ["0", "1", "2"]
