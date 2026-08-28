"""Validate a compiled report PDF before it is served.

Self-contained on purpose: real pdflatex output uses compressed object streams,
so the project's own `is_valid_pdf` (tuned to the hand-rolled writer) does not
apply. Structural validity here means a proper `%PDF` header and a trailing
`%%EOF` after a successful compile; page count is read from the compiler log.
Returns a list of *hard* problems (empty = servable); overfull/underfull boxes
are soft warnings that never block serving.
"""
from __future__ import annotations

import re

_FATAL_LOG_MARKERS = ("! LaTeX Error", "! Emergency stop", "Fatal error occurred",
                      "! Undefined control sequence")
_PAGES_RE = re.compile(r"Output written on \S+ \((\d+) pages?")


def pages_from_log(log: str) -> int:
    m = _PAGES_RE.search(log or "")
    return int(m.group(1)) if m else 0


def _structurally_valid(pdf: bytes) -> bool:
    return pdf.startswith(b"%PDF-") and b"%%EOF" in pdf[-2048:]


def validate_pdf(pdf: bytes, log: str = "", *, max_pages: int = 200) -> list[str]:
    """Return hard problems that make the PDF unservable (empty = OK)."""
    problems: list[str] = []
    if not pdf or not _structurally_valid(pdf):
        problems.append("output is not a structurally valid PDF")
        return problems
    pages = pages_from_log(log)
    if pages == 0 and b"/Page" not in pdf:
        problems.append("PDF appears to have no pages")
    if pages > max_pages:
        problems.append(f"PDF page count ({pages}) exceeds sane bound ({max_pages})")
    for marker in _FATAL_LOG_MARKERS:
        if marker in log:
            problems.append(f"LaTeX log reports a fatal issue: {marker.strip('! ')}")
            break
    return problems


def warnings(log: str) -> list[str]:
    """Non-blocking layout warnings (overfull boxes, missing refs)."""
    out: list[str] = []
    over = log.count("Overfull \\hbox")
    if over:
        out.append(f"{over} overfull hbox warning(s)")
    if "There were undefined references" in log:
        out.append("undefined references")
    return out
