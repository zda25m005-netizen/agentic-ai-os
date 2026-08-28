"""Local, dependency-free PDF generation + validation (the pdf.create tool).

A minimal but valid PDF writer (Helvetica text, word-wrapped, auto-paginated) so
we can produce real report files with **no paid API and no heavy dependency** —
CI-safe everywhere. `is_valid_pdf` / `page_count` are the verifier hooks used to
confirm a real artifact was produced (not just a "success" string).
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Letter page, 1-inch margins.
_PW, _PH = 612, 792
_LEFT, _TOP, _BOTTOM = 56, 740, 56
_LEADING = 15.0
_WRAP = 92  # chars per line at 10.5pt Helvetica (approx, conservative)


@dataclass
class Section:
    heading: str
    body: str = ""


@dataclass
class PdfDoc:
    title: str
    sections: list[Section] = field(default_factory=list)


def _esc(s: str) -> str:
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _wrap(text: str, width: int = _WRAP) -> list[str]:
    out: list[str] = []
    for raw in (text or "").splitlines() or [""]:
        if not raw.strip():
            out.append("")
            continue
        line = ""
        for word in raw.split(" "):
            if len(line) + len(word) + 1 > width:
                out.append(line)
                line = word
            else:
                line = f"{line} {word}".strip()
        out.append(line)
    return out


# One "line" = (font_size, text). Empty text = blank spacer.
def _layout(doc: PdfDoc) -> list[list[tuple[float, str]]]:
    """Break the document into pages of positioned text lines."""
    lines: list[tuple[float, str]] = [(18.0, doc.title), (0.0, "")]
    for sec in doc.sections:
        lines.append((12.5, sec.heading))
        for wl in _wrap(sec.body):
            lines.append((10.5, wl))
        lines.append((0.0, ""))

    pages: list[list[tuple[float, str]]] = []
    cur: list[tuple[float, str]] = []
    y = _TOP
    for size, text in lines:
        if y - _LEADING < _BOTTOM:
            pages.append(cur)
            cur, y = [], _TOP
        cur.append((size, text))
        y -= _LEADING
    if cur:
        pages.append(cur)
    return pages or [[(18.0, doc.title)]]


def _content_stream(page: list[tuple[float, str]]) -> bytes:
    parts = ["BT", f"{_LEADING} TL", f"{_LEFT} {_TOP} Td"]
    for size, text in page:
        if text:
            parts.append(f"/F1 {size} Tf")
            parts.append(f"({_esc(text)}) Tj")
        parts.append("T*")  # advance one line (blank spacer when no text)
    parts.append("ET")
    return ("\n".join(parts)).encode("latin-1", "replace")


def build_pdf(doc: PdfDoc) -> bytes:
    """Render a PdfDoc to valid PDF bytes."""
    pages = _layout(doc)
    objects: list[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)  # 1-based object number

    font_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    # placeholders; Pages needs kids, filled after
    page_ids: list[int] = []
    content_ids: list[int] = []
    pages_obj_id = len(objects) + 1  # reserve next number for Pages
    objects.append(b"")  # reserve slot for Pages (index pages_obj_id-1)

    for pg in pages:
        stream = _content_stream(pg)
        cid = add(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))
        content_ids.append(cid)
        pid = add(
            b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %d %d] "
            b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"
            % (pages_obj_id, _PW, _PH, font_id, cid)
        )
        page_ids.append(pid)

    kids = b" ".join(b"%d 0 R" % p for p in page_ids)
    objects[pages_obj_id - 1] = (
        b"<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, len(page_ids))
    )
    catalog_id = add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_obj_id)

    # assemble with xref
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * (len(objects) + 1)
    for i, obj in enumerate(objects, start=1):
        offsets[i] = len(out)
        out += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
    xref_pos = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for i in range(1, len(objects) + 1):
        out += b"%010d 00000 n \n" % offsets[i]
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\n" % (len(objects) + 1, catalog_id)
    out += b"startxref\n%d\n%%%%EOF" % xref_pos
    return bytes(out)


def is_valid_pdf(data: bytes) -> bool:
    return data.startswith(b"%PDF-") and b"%%EOF" in data[-32:] and b"/Type /Catalog" in data


def page_count(data: bytes) -> int:
    return data.count(b"/Type /Page /Parent")
