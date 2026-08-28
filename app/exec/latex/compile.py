"""Compile LaTeX source to PDF safely, with shell-escape disabled.

Runs pdflatex in a throwaway temp directory (twice, so page refs / LastPage /
TOC resolve), captures the log, and returns the PDF bytes. Raises
`LatexUnavailable` if no engine is installed and `LatexCompileError` (carrying
the log tail) on failure. `-no-shell-escape` and a per-run timeout make a
malicious `\\write18` inert and bound runaway compiles.
"""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

_ENGINES = ("pdflatex",)

# Standard TeX bin locations to check when the engine isn't on PATH. This makes
# the server find pdflatex even when uvicorn was launched from a shell whose
# PATH predates a MacTeX/BasicTeX/TeX Live install.
_TEX_DIRS = (
    "/Library/TeX/texbin",                       # macOS MacTeX / BasicTeX symlinks
    "/opt/homebrew/bin", "/usr/local/bin",       # Homebrew
    "/usr/bin",
)
_TEX_GLOBS = (
    "/usr/local/texlive/*/bin/*",                # Linux / macOS TeX Live
    "/opt/texlive/*/bin/*",
)


class LatexUnavailable(RuntimeError):
    """No LaTeX engine is installed."""


class LatexCompileError(RuntimeError):
    """Compilation failed; `.log` holds the tail of the compiler output."""

    def __init__(self, message: str, log: str = "") -> None:
        super().__init__(message)
        self.log = log


def latex_engine() -> str | None:
    """Absolute path (or bare name) of an available LaTeX engine, else None."""
    for eng in _ENGINES:
        found = shutil.which(eng)
        if found:
            return found
    # Not on PATH — probe well-known TeX install directories directly.
    search_dirs = list(_TEX_DIRS)
    for pattern in _TEX_GLOBS:
        search_dirs.extend(glob.glob(pattern))
    for eng in _ENGINES:
        for d in search_dirs:
            cand = os.path.join(d, eng)
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
    return None


def compile_tex(tex: str, *, timeout: float = 60.0, passes: int = 2) -> tuple[bytes, str]:
    """Compile `tex` to PDF; return (pdf_bytes, combined_log)."""
    engine = latex_engine()
    if engine is None:
        raise LatexUnavailable("no LaTeX engine found")

    # Ensure the engine's own directory is on PATH for any helper binaries it
    # calls, even when the server PATH doesn't include the TeX bin dir.
    env = dict(os.environ)
    eng_dir = os.path.dirname(engine)
    if eng_dir:
        env["PATH"] = eng_dir + os.pathsep + env.get("PATH", "")

    with tempfile.TemporaryDirectory(prefix="report-tex-") as tmp:
        d = Path(tmp)
        (d / "report.tex").write_text(tex, encoding="utf-8")
        log = ""
        for _ in range(max(1, passes)):
            try:
                proc = subprocess.run(
                    [engine, "-no-shell-escape", "-interaction=nonstopmode",
                     "-halt-on-error", "report.tex"],
                    cwd=d, capture_output=True, text=True, timeout=timeout, env=env,
                )
            except subprocess.TimeoutExpired as e:
                raise LatexCompileError("LaTeX compilation timed out", str(e)) from e
            log = proc.stdout or ""
            log_file = d / "report.log"
            if log_file.exists():
                log = log_file.read_text(encoding="utf-8", errors="replace")
            if proc.returncode != 0:
                raise LatexCompileError("pdflatex returned non-zero", log[-4000:])

        pdf_path = d / "report.pdf"
        if not pdf_path.exists() or pdf_path.stat().st_size == 0:
            raise LatexCompileError("no PDF produced", log[-4000:])
        return pdf_path.read_bytes(), log
