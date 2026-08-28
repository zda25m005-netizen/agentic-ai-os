"""LaTeX report pipeline: escaping, rendering, compile/validate, safe fallback."""
import shutil

import pytest

from app.exec.latex.escape import tex_escape, tex_url
from app.exec.latex.pipeline import render_report_best, render_report_latex
from app.exec.latex.render import render_tex
from app.exec.latex.validate import pages_from_log, validate_pdf, warnings
from app.exec.report_builder import build_report
from app.missions.models import Mission, Task
from app.missions.state import MissionStatus, TaskStatus

_HAVE_LATEX = shutil.which("pdflatex") is not None


def _task(i, d, r):
    return Task(id=i, mission_id=1, description=d, status=TaskStatus.DONE,
                depends_on=[], result=r, created_at=0.0, updated_at=0.0)


def _mission(obj="NVIDIA vs AMD AI accelerators"):
    return Mission(id=7, objective=obj, status=MissionStatus.COMPLETED, priority=1,
                   deadline=None, created_at=0.0, updated_at=0.0,
                   meta={"usage": {"tokens": 100, "usd": 0.01}, "status": "COMPLETED"})


def _report():
    tasks = [
        _task(1, "Ecosystem", "CUDA leads. https://arxiv.org/abs/1 https://reuters.com/x"),
        _task(2, "Hardware", "MI300X competitive. https://amd.com/mi300x"),
        _task(3, "Positioning", "Incumbents favored (analyst synthesis)."),
    ]
    return build_report(_mission(), tasks)


# ---- escaping / security ----

def test_escape_neutralizes_control_sequences():
    out = tex_escape(r"\input{/etc/passwd} \write18{rm -rf /} 50% & $x$ #_")
    for danger in ("\\input", "\\write18"):
        assert danger not in out          # backslash was escaped away
    for special in ("\\%", "\\&", "\\$", "\\#", "\\_"):
        assert special in out
    assert r"\textbackslash{}" in out


def test_tex_url_is_escaped_monospace():
    assert tex_url("https://x.com/a_b%c").startswith(r"\texttt{")
    assert "\\_" in tex_url("https://x.com/a_b")


# ---- rendering ----

def test_render_tex_is_wellformed_and_injection_safe():
    tex = render_tex(_report())
    assert tex.startswith(r"\documentclass")
    assert tex.strip().endswith(r"\end{document}")
    assert r"\begin{document}" in tex
    # a malicious result must not survive as a live macro
    evil = build_report(_mission(), [_task(1, "x", r"\write18{echo hacked}")])
    assert r"\write18{echo hacked}" not in render_tex(evil)


def test_render_tex_includes_key_sections():
    tex = render_tex(_report())
    for marker in ("Executive Summary", "Key Findings", "Source Register", "BOTTOM LINE"):
        assert marker in tex


# ---- validation helpers ----

def test_validate_rejects_non_pdf():
    assert validate_pdf(b"not a pdf") == ["output is not a structurally valid PDF"]


def test_pages_and_warnings_parse_log():
    assert pages_from_log("Output written on report.pdf (4 pages, 190000 bytes).") == 4
    assert warnings("Overfull \\hbox (1.0pt too wide)") == ["1 overfull hbox warning(s)"]


# ---- fallback path (no LaTeX dependency) ----

def test_best_always_returns_valid_pdf():
    pdf, engine = render_report_best(_report())
    assert pdf.startswith(b"%PDF-") and b"%%EOF" in pdf[-2048:]
    assert engine in {"LaTeX", "Fallback"}


def test_fallback_used_when_latex_missing(monkeypatch):
    # force "no engine" -> render_report_latex returns None -> Fallback engine
    monkeypatch.setattr("app.exec.latex.compile.latex_engine", lambda: None)
    assert render_report_latex(_report()) is None
    pdf, engine = render_report_best(_report())
    assert engine == "Fallback" and pdf.startswith(b"%PDF-")


# ---- real compile (only where LaTeX is installed) ----

@pytest.mark.skipif(not _HAVE_LATEX, reason="pdflatex not installed")
def test_latex_engine_produces_valid_pdf():
    pdf, engine = render_report_best(_report())
    assert engine == "LaTeX"
    assert pdf.startswith(b"%PDF-") and len(pdf) > 10_000
