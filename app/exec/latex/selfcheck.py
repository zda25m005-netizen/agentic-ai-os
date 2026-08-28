"""Diagnose whether the LaTeX report engine is usable on this machine.

Run:  python -m app.exec.latex.selfcheck

Reports the detected engine, attempts a real compile of a representative
report, and — if it fails — prints the missing package(s) and the exact
`tlmgr install` command to fix them. Exit code 0 = LaTeX ready, 1 = will use
the fallback renderer.
"""
from __future__ import annotations

import re
import sys

from app.exec.latex.compile import LatexCompileError, LatexUnavailable, compile_tex, latex_engine
from app.exec.latex.render import render_tex
from app.exec.report import EvidenceCoverage, Finding, Metric, Report, Scorecard, SourceRecord

_MISSING_RE = re.compile(r"File `([^']+)\.sty' not found")


def _sample() -> Report:
    return Report(
        title="LaTeX Engine Self-Check", subtitle="Analytical Report",
        report_type="TECHNICAL_ANALYSIS",
        meta={"mission_id": 0, "date": "self-check", "sources": 1, "status": "COMPLETED"},
        snapshot=[Metric("Engine", "LaTeX"), Metric("Status", "Testing")],
        executive_summary="A representative document exercising every package the "
                          "report template depends on.",
        findings=[Finding("Compilation", "This finding exercises callouts, badges and "
                          "traceability.", "High", source_refs=[1])],
        scorecard=Scorecard(["A", "B"], ["X", "Y"], {"X": [5, 3], "Y": [2, 4]}),
        coverage=EvidenceCoverage(1, 1, 0),
        source_records=[SourceRecord(1, "https://arxiv.org/abs/1", "arxiv.org",
                                     "Academic", "High", "Unknown")],
        freshness={"Recent": 0, "Current": 0, "Background": 0, "Unknown": 1},
    )


def main() -> int:
    eng = latex_engine()
    print(f"LaTeX engine detected: {eng or 'NONE (will use fallback renderer)'}")
    if not eng:
        print("\nInstall BasicTeX, then re-run this check:")
        print("  brew install --cask basictex")
        return 1

    tex = render_tex(_sample())
    try:
        pdf, _log = compile_tex(tex)
    except LatexUnavailable:
        print("Engine vanished between detection and compile — using fallback.")
        return 1
    except LatexCompileError as e:
        missing = sorted(set(_MISSING_RE.findall(e.log)))
        print("\nLaTeX is installed but compilation FAILED.")
        if missing:
            print("Missing package(s):", ", ".join(missing))
            print("\nFix with:")
            print("  sudo tlmgr update --self")
            print("  sudo tlmgr install " + " ".join(missing))
        else:
            print("Compiler log tail:\n" + e.log[-1500:])
        return 1

    print(f"OK — compiled a {len(pdf)} byte PDF. The report endpoint will use LaTeX.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
