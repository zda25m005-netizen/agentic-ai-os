"""Professional PDF renderer for a structured Report (no external deps).

A small layout engine over raw PDF operators: cover page, numbered sections,
executive-summary callout, findings, wrapped tables with a bold header row,
methodology, sources, and a running header + footer with real page numbers
(rendered in a second pass once the total page count is known). Helvetica +
Helvetica-Bold only. Everything is measured so nothing overflows or clips.
"""
from __future__ import annotations

import math
import re

from app.exec import markdown as md
from app.exec.report import Report, Table

_PW, _PH = 595, 842          # A4 points
_L, _R = 64, 531             # left / right text bounds
_TOP, _BOT = 72, 72          # top / bottom margins (y from top)
_INK = (0.11, 0.12, 0.15)
_MUTE = (0.42, 0.46, 0.52)
_ACCENT = (0.15, 0.42, 0.75)
_NAVY = (0.09, 0.14, 0.28)
_RULE = (0.80, 0.83, 0.87)

_URL_RE = re.compile(r"https?://\S+")


def _prose(text: str) -> str:
    """Inline body text: bare URLs removed, inline Markdown flattened to clean text."""
    s = _URL_RE.sub("", text or "")
    s = md.inline_to_plain(s)          # **bold**/`code`/[t](u) -> plain, structurally
    s = re.sub(r"\s+([.,;:])", r"\1", s)
    return re.sub(r"\s{2,}", " ", s).strip()


def _ref_label(url: str) -> str:
    """A short, human title for a reference (from the URL slug/domain)."""
    from urllib.parse import unquote
    path = url.split("?")[0].split("#")[0].rstrip("/")
    slug = path.rsplit("/", 1)[-1] if "/" in path.split("//")[-1] else ""
    label = unquote(slug).replace("_", " ").strip()
    if len(label) < 3:
        label = url.split("//")[-1].split("/")[0]
    return label[:70]


def _overall_conf(r: Report) -> str:
    confs = {f.confidence for f in r.findings}
    for level in ("High", "Medium", "Low"):
        if level in confs:
            return level
    return "Analytical"


def _esc(s: str) -> str:
    return (s or "").replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _char_w(size: float) -> float:
    return size * 0.52  # Helvetica average glyph width (conservative)


def _wrap(text: str, size: float, width: float) -> list[str]:
    max_chars = max(4, int(width / _char_w(size)))
    out: list[str] = []
    for raw in (text or "").split("\n"):
        if not raw.strip():
            out.append("")
            continue
        line = ""
        for word in raw.split(" "):
            if len(line) + len(word) + 1 > max_chars:
                if line:
                    out.append(line)
                line = word
            else:
                line = f"{line} {word}".strip()
        out.append(line)
    return out


class _Canvas:
    """Absolute-positioned drawing onto a list of pages; y measured from top."""

    def __init__(self) -> None:
        self.pages: list[list[bytes]] = [[]]
        self.y = _TOP

    def _ops(self) -> list[bytes]:
        return self.pages[-1]

    def new_page(self) -> None:
        self.pages.append([])
        self.y = _TOP

    def _pdfy(self, y_top: float) -> float:
        return _PH - y_top

    def text(self, x: float, y_top: float, size: float, s: str,
             bold: bool = False, color=_INK) -> None:
        font = "F2" if bold else "F1"
        r, g, b = color
        txt = _esc(s).encode("latin-1", "replace")
        self._ops().append(
            b"%.3f %.3f %.3f rg BT /%s %.1f Tf 1 0 0 1 %.1f %.1f Tm (%s) Tj ET"
            % (r, g, b, font.encode(), size, x, self._pdfy(y_top), txt)
        )

    def rect(self, x: float, y_top: float, w: float, h: float,
             fill=None, stroke=None, lw: float = 0.7) -> None:
        y = self._pdfy(y_top) - h
        if fill:
            self._ops().append(b"%.3f %.3f %.3f rg %.1f %.1f %.1f %.1f re f" % (*fill, x, y, w, h))
        if stroke:
            self._ops().append(
                b"%.3f %.3f %.3f RG %.1f w %.1f %.1f %.1f %.1f re S" % (*stroke, lw, x, y, w, h)
            )

    def line(self, x1: float, y1: float, x2: float, y2: float,
             color=_RULE, lw: float = 0.7) -> None:
        self._ops().append(
            b"%.3f %.3f %.3f RG %.1f w %.1f %.1f m %.1f %.1f l S"
            % (*color, lw, x1, self._pdfy(y1), x2, self._pdfy(y2))
        )

    def ensure(self, need: float) -> None:
        if self.y + need > _PH - _BOT:
            self.new_page()

    def para(self, text: str, size: float = 10.5, gap: float = 5.0,
             color=_INK, lead: float = 14.0) -> None:
        for ln in _wrap(text, size, _R - _L):
            self.ensure(lead)
            if ln:
                self.text(_L, self.y, size, ln, color=color)
            self.y += lead
        self.y += gap


def _cover(c: _Canvas, r: Report) -> None:
    c.rect(0, 0, _PW, 8, fill=_ACCENT)
    c.text(_L, 150, 9, "RESEARCH & ANALYSIS REPORT", bold=True, color=_MUTE)
    y = 300
    for ln in _wrap(r.title, 30, _R - _L):
        c.text(_L, y, 30, ln, bold=True)
        y += 38
    if r.subtitle:
        y += 6
        for ln in _wrap(r.subtitle, 15, _R - _L):
            c.text(_L, y, 15, ln, color=_MUTE)
            y += 22
    c.line(_L, y + 18, _R, y + 18, color=_ACCENT, lw=1.4)
    meta = r.meta
    lines = [
        r.report_type.replace("_", " ").title(),
        meta.get("date", ""),
        f"{meta.get('sources', 0)} source(s) referenced",
    ]
    yy = _PH - 150
    for ln in lines:
        if ln:
            c.text(_L, yy, 11, ln, color=_MUTE)
            yy += 18


def _section_title(c: _Canvas, num: int | None, title: str) -> None:
    c.ensure(40)
    c.y += 6
    label = f"{num:02d}   {title}" if num is not None else title
    c.text(_L, c.y, 14, label, bold=True, color=_ACCENT)
    c.y += 8
    c.line(_L, c.y, _R, c.y)
    c.y += 14


def _table(c: _Canvas, t: Table) -> None:
    cols = len(t.columns)
    if cols == 0:
        return
    cw = (_R - _L) / cols
    lead = 12.5

    def row(cells: list[str], bold: bool, shade: bool = False) -> None:
        wrapped = [_wrap(str(cell), 9.5, cw - 10) for cell in cells]
        h = max(len(w) for w in wrapped) * lead + 8
        c.ensure(h)
        if shade:
            c.rect(_L, c.y, _R - _L, h, fill=(0.96, 0.97, 0.98))
        for i, lines in enumerate(wrapped):
            x = _L + i * cw + 5
            yy = c.y + 12
            for ln in lines:
                c.text(x, yy, 9.5, ln, bold=bold)
                yy += lead
        c.line(_L, c.y + h, _R, c.y + h, color=_RULE, lw=0.5)
        c.y += h

    row(t.columns, bold=True, shade=True)
    for i, r in enumerate(t.rows):
        row([str(x) for x in r], bold=False, shade=(i % 2 == 1))
    if t.caption:
        c.y += 4
        c.text(_L, c.y, 8.5, t.caption, color=_MUTE)
        c.y += 12
    c.y += 8


_CONF = {"High": (0.09, 0.55, 0.34), "Medium": (0.80, 0.55, 0.10), "Low": (0.75, 0.20, 0.24)}


def _snapshot(c: _Canvas, metrics) -> None:
    cards = metrics[:4]
    if not cards:
        return
    gap = 10
    w = (_R - _L - gap * (len(cards) - 1)) / len(cards)
    c.ensure(70)
    top = c.y
    for i, m in enumerate(cards):
        x = _L + i * (w + gap)
        c.rect(x, top, w, 56, fill=(0.97, 0.98, 0.99), stroke=_RULE)
        c.text(x + 10, top + 17, 8, m.label.upper(), bold=True, color=_MUTE)
        vy = top + 36
        for ln in _wrap(m.value, 13, w - 18)[:2]:
            c.text(x + 10, vy, 13, ln, bold=True)
            vy += 14
    c.y = top + 56 + 16


def _dots(c: _Canvas, x: float, y_top: float, score: int, n: int = 5) -> None:
    box, gap = 8, 3
    for i in range(n):
        bx = x + i * (box + gap)
        if i < score:
            c.rect(bx, y_top, box, box, fill=_ACCENT)
        else:
            c.rect(bx, y_top, box, box, stroke=_RULE, lw=0.6)


_PALETTE = [_ACCENT, (0.42, 0.46, 0.52), (0.55, 0.35, 0.66), (0.10, 0.55, 0.34)]


def _scorecard(c, sc) -> None:
    """Horizontal filled bars per (entity, dimension) — the █████ look."""
    dims, ents = sc.dimensions, sc.entities
    label_w = 132
    cellw = (_R - _L - label_w) / max(len(dims), 1)
    barw = cellw - 18
    c.ensure(24)
    for j, d in enumerate(dims):
        c.text(_L + label_w + j * cellw, c.y + 11, 7.5, str(d)[:15], bold=True, color=_MUTE)
    c.y += 20
    for e in ents:
        c.ensure(22)
        c.text(_L, c.y + 13, 10, str(e)[:20], bold=True)
        row = sc.scores.get(e, [])
        for j in range(len(dims)):
            s = row[j] if j < len(row) else 0
            x = _L + label_w + j * cellw
            c.rect(x, c.y + 7, barw, 9, fill=(0.92, 0.93, 0.95))
            c.rect(x, c.y + 7, barw * (s / 5.0), 9, fill=_ACCENT)
            c.text(x + barw + 4, c.y + 14, 8, str(s), color=_MUTE)
        c.y += 22
    c.y += 5
    c.text(_L, c.y, 8.5, "Scoring: " + sc.methodology, color=_MUTE)
    c.y += 16


def _bar_chart(c, sc) -> None:
    ents = sc.entities
    totals = [sum(sc.scores.get(e, [])) for e in ents]
    maxv = (len(sc.dimensions) * 5) or 1
    ch = 118
    c.ensure(ch + 44)
    base = c.y + ch
    slot = (_R - _L) / max(len(ents), 1)
    bw = min(64, slot * 0.5)
    for i, (e, v) in enumerate(zip(ents, totals, strict=False)):
        h = ch * (v / maxv)
        x = _L + i * slot + (slot - bw) / 2
        c.rect(x, base - h, bw, h, fill=_PALETTE[i % len(_PALETTE)])
        c.text(x + 4, base - h - 4, 9, str(v), bold=True)
        c.text(x, base + 14, 9, str(e)[:14], color=_MUTE)
    c.line(_L, base, _R, base, color=_RULE)
    c.y = base + 26
    c.text(_L, c.y, 8.5,
           f"Figure 1 - Composite analyst-derived score (sum of 0-5 assessments, max {maxv}). "
           "Evidence-based, not market data.", color=_MUTE)
    c.y += 16


def _heatmap(c, sc) -> None:
    dims, ents = sc.dimensions, sc.entities
    label_w = 132
    cellw = (_R - _L - label_w) / max(len(dims), 1)
    ch = 26
    c.ensure(26)
    for j, d in enumerate(dims):
        c.text(_L + label_w + j * cellw, c.y + 11, 7.5, str(d)[:14], color=_MUTE)
    c.y += 18
    for e in ents:
        c.ensure(ch + 2)
        c.text(_L, c.y + 16, 9.5, str(e)[:20], bold=True)
        row = sc.scores.get(e, [])
        for j in range(len(dims)):
            s = row[j] if j < len(row) else 0
            frac = s / 5.0
            col = (1 - frac * 0.82, 1 - frac * 0.45, 1 - frac * 0.10)
            x = _L + label_w + j * cellw
            c.rect(x + 2, c.y + 2, cellw - 4, ch - 4, fill=col, stroke=_RULE, lw=0.4)
            tcol = (0.10, 0.12, 0.15) if frac < 0.6 else (1, 1, 1)
            c.text(x + cellw / 2 - 3, c.y + 17, 9, str(s), bold=True, color=tcol)
        c.y += ch
    c.y += 4
    c.text(_L, c.y, 8.5, "Figure 2 - Capability heatmap of analyst-derived scores "
           "(0-5), based on this mission's evidence. Not market data.", color=_MUTE)
    c.y += 16


def _radar(c, sc) -> None:
    """Outline radar/spider chart (>=3 dimensions), one polygon per entity."""
    dims, ents = sc.dimensions, sc.entities
    n = len(dims)
    if n < 3:
        return
    size = 210
    c.ensure(size + 40)
    cx = (_L + _R) / 2
    cy = c.y + size / 2
    rad = size / 2 - 14

    def pt(i: int, frac: float) -> tuple[float, float]:
        a = -math.pi / 2 + i * 2 * math.pi / n
        return cx + rad * frac * math.cos(a), cy + rad * frac * math.sin(a)

    # grid rings + spokes
    for ring in (0.25, 0.5, 0.75, 1.0):
        pts = [pt(i, ring) for i in range(n)]
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            c.line(x1, y1, x2, y2, color=(0.86, 0.88, 0.91), lw=0.5)
    for i in range(n):
        x2, y2 = pt(i, 1.0)
        c.line(cx, cy, x2, y2, color=(0.86, 0.88, 0.91), lw=0.5)
        lx, ly = pt(i, 1.12)
        c.text(lx - 14, ly, 7.5, str(dims[i])[:12], color=_MUTE)
    # entity polygons
    for k, e in enumerate(ents):
        row = sc.scores.get(e, [])
        col = _PALETTE[k % len(_PALETTE)]
        pts = [pt(i, (row[i] if i < len(row) else 0) / 5.0) for i in range(n)]
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            c.line(x1, y1, x2, y2, color=col, lw=1.5)
    # legend
    ly = cy + rad + 22
    lx = _L
    for k, e in enumerate(ents):
        col = _PALETTE[k % len(_PALETTE)]
        c.rect(lx, ly, 8, 8, fill=col)
        c.text(lx + 12, ly + 7, 8.5, str(e)[:22], color=_INK)
        lx += 150
    c.y = ly + 22
    c.text(_L, c.y, 8.5, "Figure 3 - Capability radar (qualitative assessment, 0-5).",
           color=_MUTE)
    c.y += 16


def _coverage(c, cov) -> None:
    c.ensure(40)
    pct = cov.coverage_pct
    c.rect(_L, c.y, _R - _L, 10, fill=(0.93, 0.94, 0.96))
    c.rect(_L, c.y, (_R - _L) * pct / 100, 10, fill=_ACCENT)
    c.y += 18
    c.para(f"Evidence coverage {pct}%  -  {cov.sources_analyzed} source(s) analyzed  -  "
           f"{cov.claims_supported} claim(s) source-backed  -  "
           f"{cov.assessments} analytical assessment(s).", 9.5, color=_MUTE)


def _conf_badge(c: _Canvas, x: float, y_top: float, conf: str) -> None:
    col = _CONF.get(conf, _MUTE)
    label = conf.upper()
    c.rect(x, y_top - 9, 8 + len(label) * 5.4, 13, stroke=col, lw=0.8)
    c.text(x + 5, y_top, 7.5, label, bold=True, color=col)


def _integrity(c: _Canvas, integ: dict) -> None:
    """Honest research-integrity panel — real ledger numbers, gaps shown plainly."""
    extracted = integ.get("claims_extracted", 0)
    rows = [
        ("Sources analysed", str(integ.get("sources_analyzed", 0))),
        ("Findings", str(extracted)),
        ("Source-backed", f"{integ.get('claims_supported', 0)} / {extracted}"),
        ("Unsupported", str(integ.get("unsupported", 0))),
        ("High confidence", str(integ.get("high_confidence", 0))),
        ("Unverified figures", str(integ.get("unverified_figures", 0))),
    ]
    cols, rowh, pad = 3, 34, 10
    nrows = (len(rows) + cols - 1) // cols
    h = nrows * rowh + pad
    cw = (_R - _L) / cols
    c.ensure(h + 8)
    top = c.y
    c.rect(_L, top, _R - _L, h, stroke=_RULE, lw=0.8)
    warn = integ.get("unverified_figures", 0) or (integ.get("sources_analyzed", 0) == 0)
    c.rect(_L, top, 4, h, fill=(0.80, 0.55, 0.10) if warn else _NAVY)
    for i, (label, val) in enumerate(rows):
        cx = _L + (i % cols) * cw + 12
        cy = top + (i // cols) * rowh + 15
        c.text(cx, cy, 7.5, label.upper(), bold=True, color=_MUTE)
        col = (0.75, 0.20, 0.24) if (label == "Unverified figures" and val != "0") else _INK
        c.text(cx, cy + 14, 13, val, bold=True, color=col)
    c.y = top + h + 6
    c.para("Metrics reflect this run's actual evidence ledger; no values are fabricated.",
           8.5, gap=8, color=_MUTE)


def _bottom_line(c: _Canvas, text: str) -> None:
    """Filled navy 'BOTTOM LINE' callout — the report's headline conclusion."""
    lines = _wrap(text, 10.5, _R - _L - 24)[:4]
    h = 22 + len(lines) * 14 + 10
    c.ensure(h + 8)
    top = c.y
    c.rect(_L, top, _R - _L, h, fill=_NAVY)
    c.text(_L + 12, top + 16, 8, "BOTTOM LINE", bold=True, color=(1, 1, 1))
    yy = top + 34
    for ln in lines:
        c.text(_L + 12, yy, 10.5, ln, color=(0.90, 0.93, 0.97))
        yy += 14
    c.y = top + h + 10


def _exec_confidence(c: _Canvas, r: Report) -> None:
    """Evidence-coverage bar + overall qualitative confidence badge."""
    if not r.coverage:
        return
    pct = r.coverage.coverage_pct
    c.text(_L, c.y, 8, "EVIDENCE COVERAGE", bold=True, color=_MUTE)
    c.y += 10
    c.rect(_L, c.y, _R - _L, 9, fill=(0.91, 0.93, 0.96))
    c.rect(_L, c.y, (_R - _L) * pct / 100, 9, fill=_NAVY)
    c.y += 17
    conf = r.integrity.get("overall_confidence") or _overall_conf(r)
    c.text(_L, c.y, 9, f"{pct}% of major claims source-backed  -  "
           f"{r.coverage.sources_analyzed} source(s) analysed  -  overall confidence",
           color=_MUTE)
    _conf_badge(c, _L + 340, c.y, conf)
    c.y += 16


def _bullet(c: _Canvas, marker: str, text: str, indent: float = 18) -> None:
    lines = _wrap(text, 10, _R - (_L + indent)) or [""]
    c.ensure(len(lines) * 14 + 2)
    c.text(_L + 4, c.y + 10, 10, marker, color=_MUTE)
    for ln in lines:
        c.text(_L + indent, c.y + 10, 10, ln)
        c.y += 14
    c.y += 2


def _render_blocks(c: _Canvas, blocks) -> None:
    """Render a Markdown AST onto the canvas (headings, paras, lists, code, tables)."""
    for b in blocks:
        if isinstance(b, md.Heading):
            c.ensure(22)
            c.y += 4
            c.text(_L, c.y + 10, 11, md.inline_to_plain(b.text)[:80], bold=True, color=_ACCENT)
            c.y += 18
        elif isinstance(b, md.Para):
            c.para(md.inline_to_plain(b.text), 10.5)
        elif isinstance(b, md.ListBlock):
            for i, it in enumerate(b.items, 1):
                _bullet(c, f"{i}." if b.ordered else "-", md.inline_to_plain(it))
            c.y += 4
        elif isinstance(b, md.Code):
            for ln in b.text.split("\n"):
                c.para(ln or " ", 9, gap=0, color=_MUTE)
            c.y += 4
        elif isinstance(b, md.Table):
            _table(c, Table(b.header, b.rows, ""))


def _body(c: _Canvas, r: Report) -> None:
    n = 1
    if r.snapshot:
        c.text(_L, c.y, 11, "EXECUTIVE SNAPSHOT", bold=True, color=_MUTE)
        c.y += 14
        _snapshot(c, r.snapshot)

    if r.executive_summary:
        _section_title(c, n, "Executive Summary")
        n += 1
        top = c.y
        c.para(_prose(r.executive_summary), 10.5)
        c.rect(_L - 12, top - 6, 3, (c.y - top), fill=_ACCENT)  # accent bar
        bl = _prose(r.findings[0].body) if r.findings else _prose(r.executive_summary)
        bl = (bl.split(". ")[0].rstrip(".") + ".") if bl else ""
        if bl:
            _bottom_line(c, bl[:360])

    if r.problem_definition:
        _section_title(c, n, "Problem Definition")
        n += 1
        _render_blocks(c, md.parse(md.strip_bare_urls(r.problem_definition)))

    if r.findings:
        _section_title(c, n, "Key Findings")
        n += 1
        for i, f in enumerate(r.findings, 1):
            c.ensure(30)
            c.text(_L, c.y, 11, f"{i:02d}", bold=True, color=_ACCENT)
            c.text(_L + 28, c.y, 11, f.title[:58], bold=True)
            c.y += 15
            cite = (" " + "".join(f"[{n}]" for n in f.source_refs)) if f.source_refs else ""
            c.para(_prose(f.body) + cite, 10, gap=8)

    for a in r.approaches:
        _section_title(c, n, str(a.get("name", "Approach")))
        n += 1
        if a.get("how_it_works"):
            c.text(_L, c.y + 10, 10.5, "How it works", bold=True, color=_ACCENT)
            c.y += 16
            _render_blocks(c, md.parse(md.strip_bare_urls(a["how_it_works"])))
        for label, key in (("Advantages", "advantages"), ("Disadvantages", "disadvantages"),
                           ("Failure modes", "failure_modes"), ("Mitigations", "mitigations")):
            items = a.get(key) or []
            if items:
                c.text(_L, c.y + 10, 10.5, label, bold=True, color=_ACCENT)
                c.y += 16
                for it in items:
                    _bullet(c, "-", md.inline_to_plain(str(it)))
                c.y += 2

    if r.comparative_analysis:
        _section_title(c, n, "Comparative Analysis")
        n += 1
        _render_blocks(c, md.parse(md.strip_bare_urls(r.comparative_analysis)))

    if r.scorecard:
        _section_title(c, n, "Decision Matrix")
        n += 1
        _scorecard(c, r.scorecard)
        _section_title(c, n, "Visual Analysis")
        n += 1
        _bar_chart(c, r.scorecard)
        _heatmap(c, r.scorecard)
        _radar(c, r.scorecard)

    if r.failure_analysis:
        _section_title(c, n, "Failure Mode Analysis")
        n += 1
        rows = [[d.get("failure", ""), d.get("impact", ""), d.get("mitigation", "")]
                for d in r.failure_analysis]
        _table(c, Table(["Failure", "Impact", "Mitigation"], rows, ""))

    if r.recommendation or r.decision_rationale:
        _section_title(c, n, "Recommendation")
        n += 1
        if r.recommendation:
            _render_blocks(c, md.parse(md.strip_bare_urls(r.recommendation)))
        if r.decision_rationale:
            rows = [[d.get("requirement", ""), d.get("decision", ""), d.get("reason", "")]
                    for d in r.decision_rationale]
            _table(c, Table(["Requirement", "Decision", "Reason"], rows,
                            "Decision rationale — requirement to design decision."))

    # Structured per-approach analysis replaces the generic task-result sections.
    for sec in ([] if r.approaches else r.sections):
        _section_title(c, n, sec.heading)
        n += 1
        body = md.strip_bare_urls("\n\n".join(sec.paragraphs))
        _render_blocks(c, md.parse(body))
        if sec.table:
            _table(c, sec.table)

    if r.strategic_implications:
        _section_title(c, n, "Key Takeaways")
        n += 1
        for imp in r.strategic_implications:
            c.ensure(30)
            top = c.y
            c.para(imp, 10.5, gap=8)
            c.rect(_L - 12, top - 6, 3, (c.y - top - 4), fill=_PALETTE[2])

    if r.limitations:
        _section_title(c, n, "Limitations")
        n += 1
        for lim in r.limitations:
            c.para("-  " + lim, 10, gap=3, color=_MUTE)
        c.y += 6

    if r.source_records:
        _section_title(c, n, "References")
        n += 1
        for s in r.source_records:
            _bullet(c, f"[{s.ref}]", _ref_label(s.url), indent=26)
            c.para(s.url, 8.5, gap=6, color=_MUTE)
    elif r.sources:
        _section_title(c, n, "References")
        n += 1
        for i, s in enumerate(r.sources, 1):
            c.para(f"[{i}] {s}", 9.5, gap=2, color=_MUTE)
    else:
        # No dedicated (near-empty) page — a compact, honest one-liner.
        _section_title(c, n, "References")
        n += 1
        c.para("No external references were available for this report.", 10, color=_MUTE)

    if r.appendix:
        c.new_page()
        c.text(_L, c.y, 13, "APPENDIX", bold=True, color=_MUTE)
        c.y += 22
        for sec in r.appendix:
            _section_title(c, None, sec.heading)
            for p in sec.paragraphs:
                c.para(p, 10)
            if sec.table:
                _table(c, sec.table)


def render_report(r: Report) -> bytes:
    c = _Canvas()
    _cover(c, r)
    c.new_page()
    _body(c, r)

    total = len(c.pages)

    def _label(text: str, y_top: float, x: float = _L) -> bytes:
        rr, gg, bb = _MUTE
        body = _esc(text)[:96].encode("latin-1", "replace")
        return (b"%.3f %.3f %.3f rg BT /F1 8 Tf 1 0 0 1 %.1f %.1f Tm (%s) Tj ET"
                % (rr, gg, bb, x, _PH - y_top, body))

    # De-branded running header (title only) + footer (page numbers only).
    for idx, ops in enumerate(c.pages, 1):
        if idx == 1:
            continue
        ops.insert(0, _label(r.title[:92], 44.0))
        ops.append(b"%.3f %.3f %.3f RG 0.5 w %.1f %.1f m %.1f %.1f l S"
                   % (*_RULE, _L, 52.0, _R, 52.0))
        footer = f"Page {idx} of {total}"
        ops.append(_label(footer, _PH - 40.0, x=_R - 60))

    return _assemble(c.pages)


def _assemble(pages: list[list[bytes]]) -> bytes:
    objects: list[bytes] = []

    def add(o: bytes) -> int:
        objects.append(o)
        return len(objects)

    f1 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    f2 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    pages_id = len(objects) + 1
    objects.append(b"")  # reserve Pages
    page_ids: list[int] = []
    for ops in pages:
        stream = b"\n".join(ops) or b" "
        cid = add(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))
        pid = add(
            b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %d %d] "
            b"/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> /Contents %d 0 R >>"
            % (pages_id, _PW, _PH, f1, f2, cid)
        )
        page_ids.append(pid)
    kids = b" ".join(b"%d 0 R" % p for p in page_ids)
    objects[pages_id - 1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, len(page_ids))
    cat = add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id)

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offs = [0] * (len(objects) + 1)
    for i, o in enumerate(objects, 1):
        offs[i] = len(out)
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for i in range(1, len(objects) + 1):
        out += b"%010d 00000 n \n" % offs[i]
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF" % (
        len(objects) + 1, cat, xref)
    return bytes(out)
