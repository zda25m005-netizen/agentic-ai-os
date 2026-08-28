"""Make LLM/agent-derived text safe to inject into a LaTeX document.

Security model: dynamic content is *data*, never code. Every LaTeX special
character is escaped so no control sequence can survive — a string like
``\\input{/etc/passwd}`` or ``\\write18{rm -rf}`` becomes literal, printable
text. There is no allowlist of "safe commands" because we never pass commands
through; the renderer supplies all structure itself. Compilation additionally
runs with ``-no-shell-escape`` (see compile.py), so ``\\write18`` is inert even
if it somehow appeared.
"""
from __future__ import annotations

import re

# Single-pass mapping so replacements never cascade onto each other
# (e.g. the braces inside "\textbackslash{}" must not be re-escaped).
_MAP = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}
_SPECIALS = re.compile("|".join(re.escape(k) for k in _MAP))


def tex_escape(text: str | None) -> str:
    """Escape a plain string for safe use in LaTeX text mode."""
    s = str(text if text is not None else "")
    s = _SPECIALS.sub(lambda m: _MAP[m.group()], s)
    # Normalize characters that break inputenc/PDF strings.
    s = s.replace("–", "--").replace("—", "---")
    s = s.replace("‘", "`").replace("’", "'")
    s = s.replace("“", "``").replace("”", "''")
    s = s.replace("→", r"$\rightarrow$").replace("·", r"$\cdot$")
    s = s.replace("…", "...")
    return s


def tex_url(url: str | None) -> str:
    """Render a URL as escaped monospace text (non-executing, compile-safe)."""
    return r"\texttt{" + tex_escape(url) + "}"
