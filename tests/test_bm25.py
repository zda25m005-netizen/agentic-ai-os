from app.rag.bm25 import BM25Index, tokenize


def test_tokenize_lowercases_and_splits():
    assert tokenize("Hello, SKU-4471 World!") == ["hello", "sku", "4471", "world"]


def _build() -> BM25Index:
    idx = BM25Index()
    idx.add("1", "the quick brown fox jumps over the lazy dog", {"t": "fox"})
    idx.add("2", "invoice SKU-4471 shipped to warehouse in Berlin", {"t": "sku"})
    idx.add("3", "machine learning models require training data", {"t": "ml"})
    return idx


def test_exact_term_match_ranks_first():
    idx = _build()
    hits = idx.search("SKU-4471", limit=3)
    assert hits
    assert hits[0].payload["t"] == "sku"


def test_search_returns_relevant_only():
    idx = _build()
    hits = idx.search("training data", limit=5)
    assert hits[0].payload["t"] == "ml"
    # Documents with zero matching terms are excluded.
    assert all(h.payload["t"] != "fox" for h in hits)


def test_empty_query_or_index_returns_nothing():
    assert _build().search("   ") == []
    assert BM25Index().search("anything") == []


def test_respects_limit():
    idx = BM25Index()
    for i in range(10):
        idx.add(str(i), f"common word document number {i}", {"i": i})
    hits = idx.search("common word", limit=3)
    assert len(hits) == 3


def test_len_reports_doc_count():
    assert len(_build()) == 3
