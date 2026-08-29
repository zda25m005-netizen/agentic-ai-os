"""Deep research parsers: Wikipedia full extract + arXiv (offline, pure)."""
from app.tools.deep_search import parse_arxiv, parse_extract

_ARXIV_XML = """<feed>
<entry>
  <id>http://arxiv.org/abs/2005.11401v4</id>
  <title>Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks</title>
  <summary>We explore a general-purpose fine-tuning recipe for retrieval-augmented
  generation, combining a parametric and non-parametric memory.</summary>
  <published>2020-05-22T00:00:00Z</published>
</entry>
<entry>
  <id>http://arxiv.org/abs/1911.00172v2</id>
  <title>Generalization through Memorization: Nearest Neighbor Language Models</title>
  <summary>kNN-LM interpolates a language model with nearest-neighbour retrieval.</summary>
  <published>2019-11-01T00:00:00Z</published>
</entry>
</feed>"""


def test_parse_arxiv_returns_real_papers():
    out = parse_arxiv(_ARXIV_XML, max_results=2)
    assert len(out) == 2
    assert out[0]["url"] == "https://arxiv.org/abs/2005.11401v4"      # https + real id
    assert "Retrieval-Augmented Generation" in out[0]["title"]
    assert "retrieval-augmented" in out[0]["snippet"].lower()
    assert out[0]["publisher"] == "arxiv.org" and out[0]["published"] == "2020-05-22"


def test_parse_arxiv_respects_limit_and_handles_empty():
    assert len(parse_arxiv(_ARXIV_XML, max_results=1)) == 1
    assert parse_arxiv("", 3) == []


def test_parse_semanticscholar_real_papers_with_authors():
    from app.tools.deep_search import parse_semanticscholar
    data = {"data": [
        {"title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
         "abstract": "We explore a general-purpose fine-tuning recipe for RAG.",
         "year": 2020, "authors": [{"name": "Patrick Lewis"}, {"name": "Ethan Perez"}],
         "externalIds": {"ArXiv": "2005.11401"}, "venue": "NeurIPS"},
        {"title": "kNN-LM", "abstract": "Nearest neighbour LM.", "year": 2019,
         "authors": [{"name": "Urvashi Khandelwal"}], "externalIds": {"DOI": "10.1/x"}},
        {"title": "No id paper", "abstract": "x", "externalIds": {}, "url": ""},  # dropped
    ]}
    out = parse_semanticscholar(data, 6)
    assert len(out) == 2                                   # the id-less paper is dropped
    assert out[0]["url"] == "https://arxiv.org/abs/2005.11401"
    assert out[0]["authors"][0] == "Patrick Lewis" and out[0]["year"] == 2020
    assert out[0]["venue"] == "NeurIPS"
    assert out[1]["url"] == "https://doi.org/10.1/x"        # DOI fallback


def test_parse_extract_pulls_full_paragraph():
    data = {"query": {"pages": {"123": {
        "title": "Retrieval-augmented generation",
        "extract": "Retrieval-augmented generation (RAG) is a technique.\n\n"
                   "It grounds a language model in an external corpus."}}}}
    text = parse_extract(data)
    assert "grounds a language model" in text          # multi-paragraph content
    assert "\n\n" not in text                            # normalised
    assert parse_extract({"query": {"pages": {}}}) == ""
