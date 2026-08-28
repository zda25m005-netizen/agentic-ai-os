"""Chart engine + LaTeX embedding + fallback radar (qualitative-only, honest)."""
import shutil

import pytest

from app.exec.charts import bar_chart_pdf, radar_chart_pdf, scorecard_assets
from app.exec.report import EvidenceCoverage, Finding, Report, Scorecard
from app.exec.report_pdf import render_report

_HAVE_LATEX = shutil.which("pdflatex") is not None


def _scorecard():
    return Scorecard(
        ["Accuracy", "Cost", "Freshness", "Scalability"],
        ["RAG", "Fine-Tuning", "Structured Memory"],
        {"RAG": [4, 2, 3, 3], "Fine-Tuning": [5, 3, 4, 2], "Structured Memory": [3, 4, 3, 5]},
    )


def _report(sc):
    r = Report(title="RAG vs Fine-Tuning vs Structured Memory", scorecard=sc,
               findings=[Finding("F", "Qualitative comparison.", "Analytical")],
               coverage=EvidenceCoverage(0, 0, 1))
    return r


def test_charts_are_vector_pdfs():
    sc = _scorecard()
    bar, radar = bar_chart_pdf(sc), radar_chart_pdf(sc)
    assert bar and bar.startswith(b"%PDF-")
    assert radar and radar.startswith(b"%PDF-")


def test_no_scorecard_no_charts():
    assert scorecard_assets(None) == {}
    # a 2-dimension scorecard is too small for a radar
    sc2 = Scorecard(["A", "B"], ["X"], {"X": [3, 4]})
    assert "chart_radar.pdf" not in scorecard_assets(sc2)


def test_assets_keys_match_template():
    assets = scorecard_assets(_scorecard())
    assert set(assets) == {"chart_bar.pdf", "chart_radar.pdf"}


def test_fallback_radar_renders_without_charts_dependency():
    # the dependency-free renderer draws its own radar; must produce a valid PDF
    pdf = render_report(_report(_scorecard()))
    assert pdf.startswith(b"%PDF-") and b"%%EOF" in pdf[-64:]


@pytest.mark.skipif(not _HAVE_LATEX, reason="pdflatex not installed")
def test_latex_embeds_chart_assets():
    from app.exec.latex.compile import compile_tex
    from app.exec.latex.render import render_tex
    sc = _scorecard()
    assets = scorecard_assets(sc)
    tex = render_tex(_report(sc), chart_keys=set(assets))
    assert "chart_bar.pdf" in tex and "includegraphics" in tex
    pdf, _log = compile_tex(tex, assets)
    assert pdf.startswith(b"%PDF-") and len(pdf) > 10_000
