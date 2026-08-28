"""Professional PDF renderer for a structured Report (no external deps).

A small layout engine over raw PDF operators: cover page, numbered sections,
executive-summary callout, findings, wrapped tables with a bold header row,
methodology, sources, and a running header + footer with real page numbers
(rendered in a second pass once the total page count is known). Helvetica +
Helvetica-Bold only. Everything is measured so nothing overflows or clips.
"""
from __future__ import annotations

from app.exec.report import Report, Table

_PW, _PH = 595, 842          # A4 points
_L, _R = 64, 531             # left / right text bounds
_TOP, _BOT = 72, 72          # top / bottom margins (y from top)
_INK = (0.11, 0.12, 0.15)
_MUTE = (0.42, 0.46, 0.52)
_ACCENT = (0.15, 0.42, 0.75)
_RULE = (0.80, 0.83, 0.87)


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
    c.text(_L, 150, 9, "AGENTIC AI OS  ·  ANALYTICAL REPORT", bold=True, color=_MUTE)
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
        f"Mission #{meta.get('mission_id', '—')}",
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
           f"Figure 1 - Composite capability score (sum of qualitative assessments, max {maxv}).",
           color=_MUTE)
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
    c.text(_L, c.y, 8.5, "Figure 2 - Capability heatmap (qualitative assessment, 0-5).",
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


def _trail(c, tr) -> None:
    c.para(f"{tr.sources_used} source(s) used  -  {tr.sources_excluded} excluded  -  "
           f"last verified {tr.last_verified}.", 9.5, gap=6, color=_MUTE)
    for a in tr.areas:
        c.ensure(15)
        c.rect(_L, c.y + 2, 6, 6, fill=(0.09, 0.55, 0.34))
        c.text(_L + 13, c.y + 9, 10, a)
        c.y += 15
    c.y += 6


def _conf_badge(c: _Canvas, x: float, y_top: float, conf: str) -> None:
    col = _CONF.get(conf, _MUTE)
    label = conf.upper()
    c.rect(x, y_top - 9, 8 + len(label) * 5.4, 13, stroke=col, lw=0.8)
    c.text(x + 5, y_top, 7.5, label, bold=True, color=col)


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
        c.para(r.executive_summary, 10.5)
        c.rect(_L - 12, top - 6, 3, (c.y - top), fill=_ACCENT)  # accent bar

    if r.findings:
        _section_title(c, n, "Key Findings")
        n += 1
        for i, f in enumerate(r.findings, 1):
            c.ensure(30)
            c.text(_L, c.y, 11, f"{i:02d}", bold=True, color=_ACCENT)
            c.text(_L + 28, c.y, 11, f.title[:58], bold=True)
            _conf_badge(c, _R - 62, c.y, f.confidence)
            c.y += 15
            c.para(f.body, 10, gap=4)
            if f.source_refs:
                refs = ", ".join(f"[{r}]" for r in f.source_refs)
                c.para(f"Traceability: cites source(s) {refs}  -  see Source Register.",
                       8.5, gap=8, color=_ACCENT)
            elif f.evidence:
                c.para("Evidence: " + "   ".join(f.evidence), 8.5, gap=8, color=_ACCENT)

    if r.scorecard:
        _section_title(c, n, "Competitive Scorecard")
        n += 1
        _scorecard(c, r.scorecard)
        _section_title(c, n, "Visual Analysis")
        n += 1
        _bar_chart(c, r.scorecard)
        _heatmap(c, r.scorecard)

    if r.coverage:
        _section_title(c, n, "Evidence Coverage")
        n += 1
        _coverage(c, r.coverage)
        if r.source_records:
            fr = r.freshness or {}
            c.para(
                "Source freshness  -  Recent: {r}  ·  Current: {c}  ·  "
                "Background: {b}  ·  Unknown: {u}.".format(
                    r=fr.get("Recent", 0), c=fr.get("Current", 0),
                    b=fr.get("Background", 0), u=fr.get("Unknown", 0)),
                9.5, color=_MUTE)

    if r.trail:
        _section_title(c, n, "Research Trail")
        n += 1
        _trail(c, r.trail)

    for sec in r.sections:
        _section_title(c, n, sec.heading)
        n += 1
        for p in sec.paragraphs:
            c.para(p, 10.5)
        if sec.table:
            _table(c, sec.table)

    if r.strategic_implications:
        _section_title(c, n, "Strategic Implications")
        n += 1
        for imp in r.strategic_implications:
            c.ensure(30)
            top = c.y
            c.para(imp, 10.5, gap=8)
            c.rect(_L - 12, top - 6, 3, (c.y - top - 4), fill=_PALETTE[2])

    if r.methodology:
        _section_title(c, n, "Methodology")
        n += 1
        c.para(r.methodology, 10, color=_MUTE)

    if r.limitations:
        _section_title(c, n, "Limitations")
        n += 1
        for lim in r.limitations:
            c.para("-  " + lim, 10, gap=3, color=_MUTE)
        c.y += 6

    _section_title(c, n, "Source Register")
    n += 1
    if r.source_records:
        t = Table(
            ["#", "Source", "Type", "Cred.", "Freshness"],
            [[str(s.ref), s.url, s.stype, s.credibility, s.freshness]
             for s in r.source_records],
            "Source register - type, credibility, and freshness are internal analyst "
            "assessments (heuristic), not objective ratings.",
        )
        _table(c, t)
    elif r.sources:
        for i, s in enumerate(r.sources, 1):
            c.para(f"[{i}] {s}", 9.5, gap=2, color=_MUTE)
    else:
        c.para("External source verification was not available for this analysis.",
               10, color=_MUTE)

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
    mid = r.meta.get("mission_id", "-")

    def _label(text: str, y_top: float) -> bytes:
        rr, gg, bb = _MUTE
        body = _esc(text)[:96].encode("latin-1", "replace")
        return (b"%.3f %.3f %.3f rg BT /F1 8 Tf 1 0 0 1 %.1f %.1f Tm (%s) Tj ET"
                % (rr, gg, bb, _L, _PH - y_top, body))

    # header + footer on every content page (page 1 is the cover)
    for idx, ops in enumerate(c.pages, 1):
        if idx == 1:
            continue
        ops.insert(0, _label(f"AGENTIC AI OS  -  {r.title}", 44.0))
        ops.append(b"%.3f %.3f %.3f RG 0.5 w %.1f %.1f m %.1f %.1f l S"
                   % (*_RULE, _L, 52.0, _R, 52.0))
        footer = f"Agentic AI OS  ·  Mission #{mid}  ·  Generated report  ·  Page {idx} of {total}"
        ops.append(_label(footer, _PH - 40.0))

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
