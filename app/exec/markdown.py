"""Structural Markdown parser: LLM Markdown -> document AST -> LaTeX / blocks.

The pipeline is `text -> parse() -> [Block] -> to_latex()`, never a set of global
regex substitutions. Block structure (headings, paragraphs, ordered/unordered
lists, fenced code, GFM tables) is preserved so the renderer can lay each element
out properly instead of leaking raw `###`, `**`, or `-` into the PDF. Inline
emphasis (`**bold**`, `*italic*`, `` `code` ``, `[text](url)`) is converted with
correct LaTeX escaping.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# --- AST blocks ---------------------------------------------------------------


@dataclass
class Heading:
    level: int
    text: str


@dataclass
class Para:
    text: str


@dataclass
class ListBlock:
    ordered: bool
    items: list[str] = field(default_factory=list)


@dataclass
class Code:
    text: str


@dataclass
class Table:
    header: list[str]
    rows: list[list[str]] = field(default_factory=list)


Block = Heading | Para | ListBlock | Code | Table

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_LIST = re.compile(r"^(\s*)([-*+]|\d+\.)\s+(.*)$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}")
_BARE_URL = re.compile(r"(?<!\()(?<!\]\()https?://[^\s)]+")


def _split_row(line: str) -> list[str]:
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def strip_bare_urls(text: str) -> str:
    """Remove standalone URLs (kept in the Source Register); keep markdown links."""
    return _BARE_URL.sub("", text or "")


def parse(md: str) -> list[Block]:
    """Parse Markdown into an ordered list of block elements."""
    lines = (md or "").replace("\r\n", "\n").split("\n")
    blocks: list[Block] = []
    para: list[str] = []
    n = len(lines)
    i = 0

    def flush() -> None:
        nonlocal para
        if para:
            text = " ".join(x.strip() for x in para).strip()
            if text:
                blocks.append(Para(text))
            para = []

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            flush()
            i += 1
            code: list[str] = []
            while i < n and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1  # closing fence
            blocks.append(Code("\n".join(code)))
            continue

        m = _HEADING.match(stripped)
        if m:
            flush()
            blocks.append(Heading(len(m.group(1)), m.group(2).strip()))
            i += 1
            continue

        if "|" in stripped and i + 1 < n and "|" in lines[i + 1] and _TABLE_SEP.match(lines[i + 1]):
            flush()
            header = _split_row(stripped)
            i += 2
            rows: list[list[str]] = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append(_split_row(lines[i]))
                i += 1
            blocks.append(Table(header, rows))
            continue

        lm = _LIST.match(line)
        if lm:
            flush()
            ordered = bool(re.match(r"\d+\.", lm.group(2)))
            items: list[str] = []
            while i < n:
                lm2 = _LIST.match(lines[i])
                if not lm2:
                    break
                items.append(lm2.group(3).strip())
                i += 1
            blocks.append(ListBlock(ordered, items))
            continue

        if not stripped:
            flush()
            i += 1
            continue

        para.append(line)
        i += 1

    flush()
    return blocks


# --- inline conversion --------------------------------------------------------

_INLINE = re.compile(
    r"`([^`]+)`"                      # code
    r"|\*\*([^*]+)\*\*|__([^_]+)__"   # bold
    r"|\*([^*]+)\*|_([^_]+)_"         # italic
    r"|\[([^\]]+)\]\(([^)]+)\)"       # link
)


def inline_to_latex(text: str, esc) -> str:
    """Convert inline Markdown to LaTeX using `esc` to escape literal text."""
    out: list[str] = []
    pos = 0
    for m in _INLINE.finditer(text or ""):
        out.append(esc(text[pos:m.start()]))
        if m.group(1) is not None:
            out.append(r"\texttt{" + esc(m.group(1)) + "}")
        elif m.group(2) is not None or m.group(3) is not None:
            out.append(r"\textbf{" + esc(m.group(2) or m.group(3)) + "}")
        elif m.group(4) is not None or m.group(5) is not None:
            out.append(r"\textit{" + esc(m.group(4) or m.group(5)) + "}")
        elif m.group(6) is not None:
            out.append(esc(m.group(6)))  # link text; URL lives in the register
        pos = m.end()
    out.append(esc(text[pos:]))
    return "".join(out)


_ASCII_ART = {ord(k): v for k, v in {
    "│": "|", "┃": "|", "║": "|", "┆": "|", "┇": "|",
    "─": "-", "━": "-", "┄": "-", "═": "-",
    "┌": "+", "┐": "+", "└": "+", "┘": "+", "├": "+", "┤": "+", "┬": "+", "┴": "+",
    "┼": "+", "╔": "+", "╗": "+", "╚": "+", "╝": "+", "╠": "+", "╣": "+",
    "▼": "v", "▽": "v", "▲": "^", "△": "^", "◄": "<", "►": ">", "◆": "*", "■": "*",
    "↓": "v", "↑": "^", "→": "->", "←": "<-", "⟶": "->", "⇒": "=>", "⟵": "<-",
    "•": "-", "·": "-", "●": "*", "○": "o", "”": '"', "“": '"', "’": "'", "‘": "'",
}.items()}


def to_ascii_art(text: str) -> str:
    """Map unicode box-drawing / arrows to ASCII so diagrams render in any engine."""
    return (text or "").translate(_ASCII_ART)


def inline_to_plain(text: str) -> str:
    """Strip inline Markdown to clean text (for the raw-PDF fallback canvas)."""
    # code/bold/italic keep inner text; links keep link text
    s = re.sub(r"`([^`]+)`", r"\1", text or "")
    s = re.sub(r"\*\*([^*]+)\*\*|__([^_]+)__", lambda m: m.group(1) or m.group(2), s)
    s = re.sub(r"\*([^*]+)\*|_([^_]+)_", lambda m: m.group(1) or m.group(2), s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", s)
    return s


# --- LaTeX rendering ----------------------------------------------------------


def to_latex(blocks: list[Block], esc, table_fn=None) -> str:
    """Render an AST to LaTeX. `esc` escapes text; `table_fn(header, rows)` -> str."""
    parts: list[str] = []
    for b in blocks:
        if isinstance(b, Heading):
            cmd = "subsection" if b.level <= 2 else "subsubsection"
            parts.append(f"\\{cmd}*{{" + esc(b.text) + "}")
        elif isinstance(b, Para):
            parts.append(inline_to_latex(b.text, esc))
        elif isinstance(b, ListBlock):
            env = "enumerate" if b.ordered else "itemize"
            items = "".join(r"\item " + inline_to_latex(it, esc) for it in b.items)
            parts.append(f"\\begin{{{env}}}[leftmargin=15pt,itemsep=2pt,topsep=3pt]"
                         + items + f"\\end{{{env}}}")
        elif isinstance(b, Code):
            # preserve alignment: escape, non-collapsing spaces, tight single breaks
            lines = "\\\\\n".join(esc(ln).replace(" ", "~") or "~"
                                  for ln in b.text.split("\n"))
            parts.append(r"\begingroup\setlength{\parskip}{0pt}\ttfamily\footnotesize "
                         r"\noindent " + lines + r"\par\endgroup")
        elif isinstance(b, Table) and table_fn is not None:
            parts.append(table_fn(b.header, b.rows))
    return "\n\n".join(p for p in parts if p)
