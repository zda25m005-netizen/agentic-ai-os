"""Orchestrate LaTeX rendering with a guaranteed fallback.

`render_report_latex` returns PDF bytes if (and only if) LaTeX is installed,
compiles, and validates; otherwise it returns None. `render_report_best` wraps
it and always returns a servable PDF plus the engine name, degrading to the
dependency-free renderer instead of ever raising or returning a broken file.
"""
from __future__ import annotations

import logging

from app.exec.latex.compile import LatexCompileError, LatexUnavailable, compile_tex
from app.exec.latex.render import render_tex
from app.exec.latex.validate import validate_pdf
from app.exec.report import Report

log = logging.getLogger(__name__)


def render_report_latex(report: Report) -> bytes | None:
    """Render via LaTeX; return None if unavailable, failed, or invalid."""
    try:
        from app.exec.charts import scorecard_assets  # lazy: matplotlib optional
        assets = scorecard_assets(report.scorecard)
        tex = render_tex(report, chart_keys=set(assets))
        pdf, compile_log = compile_tex(tex, assets)
    except LatexUnavailable:
        return None
    except LatexCompileError as e:
        log.warning("LaTeX compile failed, falling back: %s", e)
        return None
    except Exception as e:  # never let report rendering take down the request
        log.warning("Unexpected LaTeX error, falling back: %s", e)
        return None
    problems = validate_pdf(pdf, compile_log)
    if problems:
        log.warning("LaTeX PDF failed validation, falling back: %s", problems)
        return None
    return pdf


def render_report_best(report: Report) -> tuple[bytes, str]:
    """Return (pdf_bytes, engine) — 'LaTeX' when possible, else 'Fallback'."""
    pdf = render_report_latex(report)
    if pdf is not None:
        return pdf, "LaTeX"
    from app.exec.report_pdf import render_report  # lazy: avoid import cycle
    return render_report(report), "Fallback"
