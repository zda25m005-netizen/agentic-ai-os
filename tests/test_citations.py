from app.rag import citations
from app.rag.vectorstore import SearchHit


def _hits() -> list[SearchHit]:
    return [
        SearchHit(id="1", score=0.9,
                  payload={"text": "Revenue grew 12%.", "source": "q3.pdf", "chunk_index": 0}),
        SearchHit(id="2", score=0.8,
                  payload={"text": "APAC led growth.", "source": "q3.pdf", "chunk_index": 1}),
        SearchHit(id="3", score=0.7,
                  payload={"text": "Costs rose 3%.", "source": "q3.pdf", "chunk_index": 2}),
    ]


def test_build_messages_requests_inline_citations():
    msgs = citations.build_messages("How did revenue do?", _hits())
    assert "square brackets" in msgs[0]["content"]
    assert "[1]" in msgs[1]["content"]  # numbered context present


def test_parse_citations_maps_markers_to_hits():
    answer = "Revenue grew 12% [1], driven by APAC [2]."
    cited = citations.parse_citations(answer, _hits())
    assert [c.marker for c in cited] == [1, 2]
    assert cited[0].source == "q3.pdf"
    assert cited[1].chunk_index == 1


def test_parse_citations_ignores_out_of_range_and_dupes():
    answer = "Growth [2] was strong [2], but [9] is invalid, and [1] too."
    cited = citations.parse_citations(answer, _hits())
    # [2] once (dedup), [9] dropped (out of range), [1] kept — order of appearance.
    assert [c.marker for c in cited] == [2, 1]


def test_parse_citations_none_when_uncited():
    assert citations.parse_citations("No citations here.", _hits()) == []
