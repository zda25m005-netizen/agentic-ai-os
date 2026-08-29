"""Claim extraction: atomic claims, epistemic status, source linkage, dedup."""
from app.analysis.artifact import StatementType, Verification
from app.analysis.claims import classify_statement, extract_claims, strip_noise


def test_strip_noise_removes_urls_and_sources_block():
    t = "RAG grounds answers. See https://x.com/a.\n\nSources:\nhttps://y.com"
    out = strip_noise(t)
    assert "http" not in out and "Sources:" not in out
    assert "RAG grounds answers" in out


def test_classify_statement_epistemics():
    assert classify_statement("Companies should adopt hybrid retrieval.", True) \
        == StatementType.RECOMMENDATION
    assert classify_statement("This may increase latency.", True) == StatementType.INFERENCE
    assert classify_statement("CUDA is a GPU platform.", True) == StatementType.FACT
    assert classify_statement("CUDA is a GPU platform.", False) == StatementType.OBSERVATION


def test_extract_links_sources_and_ids():
    text = ("Vector retrieval fetches documents at query time. It may add latency. "
            "Teams should combine it with a reranker.")
    claims = extract_claims(text, ["S1", "S2"], entities=["Vector retrieval"])
    assert [c.id for c in claims] == ["C1", "C2", "C3"]
    assert all(c.source_ids == ["S1", "S2"] for c in claims)
    assert all(c.verification == Verification.PARTIALLY_VERIFIED for c in claims)
    assert claims[0].statement_type == StatementType.FACT
    assert claims[1].statement_type == StatementType.INFERENCE
    assert claims[2].statement_type == StatementType.RECOMMENDATION
    assert claims[0].entity == "Vector retrieval"
    assert claims[1].category == "performance"       # "latency"


def test_unsourced_claims_are_unverified():
    claims = extract_claims("Structured memory stores explicit facts.", [])
    assert claims[0].verification == Verification.UNVERIFIED
    assert claims[0].statement_type == StatementType.OBSERVATION


def test_headings_and_short_fragments_dropped_and_deduped():
    text = "### Heading\nRAG grounds answers in documents. RAG grounds answers in documents."
    claims = extract_claims(text, ["S1"])
    # heading filtered, duplicate collapsed -> exactly one claim
    assert len(claims) == 1
    assert "Heading" not in claims[0].statement
