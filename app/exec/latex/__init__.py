"""LaTeX rendering pipeline for professional report PDFs.

The structured `Report` IR (app/exec/report.py) is rendered to a modular LaTeX
document, compiled with pdflatex (no shell escape), validated, and served. If
LaTeX is unavailable or compilation fails, the pipeline falls back to the
dependency-free raw-PDF renderer — it never returns a broken PDF.

Public entry point: `render_report_best(report) -> (pdf_bytes, engine)`.
"""
from __future__ import annotations

from app.exec.latex.pipeline import render_report_best, render_report_latex

__all__ = ["render_report_best", "render_report_latex"]
