"""Citations: clean arXiv/DOI labels and version-tolerant metadata matching."""

from app.analysis.artifact import ArtifactSource, _academic_label, normalize_url


def test_academic_label():
    assert _academic_label("https://arxiv.org/abs/2502.16090") == "arXiv:2502.16090"
    assert _academic_label("https://arxiv.org/pdf/2308.04026") == "arXiv:2308.04026"
    assert (
        _academic_label("https://doi.org/10.1007/s40747-025-02019-z")
        == "doi:10.1007/s40747-025-02019-z"
    )
    assert _academic_label("https://en.wikipedia.org/wiki/RAG") == ""


def test_normalize_url_strips_arxiv_version_and_slash():
    assert (
        normalize_url("https://arxiv.org/abs/2502.16090v2/") == "https://arxiv.org/abs/2502.16090"
    )
    assert normalize_url("https://arxiv.org/abs/2502.16090") == "https://arxiv.org/abs/2502.16090"


def test_arxiv_citation_shows_id_not_domain():
    s = ArtifactSource.from_url("S1", "https://arxiv.org/abs/2502.16090")
    assert s.citation() == "arXiv:2502.16090."  # not "arxiv.org."


def test_enriched_arxiv_citation_uses_real_metadata():
    s = ArtifactSource.from_url("S1", "https://arxiv.org/abs/2502.16090")
    s.enrich(
        {
            "title": "Memory in Language Model Agents",
            "authors": ["Chen", "Li"],
            "year": 2025,
            "venue": "NeurIPS",
        }
    )
    cite = s.citation()
    assert "Chen et al. (2025)" in cite and "Memory in Language Model Agents" in cite
