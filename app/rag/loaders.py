"""Document loaders: file → Document(text + metadata).

Day 8: PDF. DOCX/PPTX/XLSX follow in the next days, all returning the same
Document shape so the chunking/embedding pipeline stays format-agnostic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader


@dataclass
class Document:
    """A loaded document, normalized across formats."""

    text: str
    metadata: dict = field(default_factory=dict)


class UnsupportedFormatError(ValueError):
    """Raised when a file extension has no registered loader."""


def load_pdf(path: str | Path) -> Document:
    """Extract text from a PDF, page by page.

    Page breaks are preserved as double newlines; per-page text is also
    stored in metadata so citations can reference page numbers later.
    """
    path = Path(path)
    reader = PdfReader(path)

    pages: list[str] = []
    for page in reader.pages:
        pages.append((page.extract_text() or "").strip())

    text = "\n\n".join(p for p in pages if p)
    return Document(
        text=text,
        metadata={
            "source": path.name,
            "filetype": "pdf",
            "num_pages": len(reader.pages),
            "pages": pages,
        },
    )


_LOADERS = {
    ".pdf": load_pdf,
}


def load(path: str | Path) -> Document:
    """Load any supported file by extension."""
    path = Path(path)
    loader = _LOADERS.get(path.suffix.lower())
    if loader is None:
        supported = ", ".join(sorted(_LOADERS))
        raise UnsupportedFormatError(
            f"No loader for '{path.suffix}'. Supported: {supported}"
        )
    return loader(path)
