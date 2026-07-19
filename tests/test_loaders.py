from pathlib import Path

import pytest
from pypdf import PdfWriter

from app.rag.loaders import UnsupportedFormatError, load, load_pdf


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Generate a small 2-page PDF on the fly (no binary fixtures in git)."""
    from pypdf.generic import RectangleObject

    writer = PdfWriter()
    for _ in range(2):
        writer.add_blank_page(width=612, height=792)
    pdf_path = tmp_path / "sample.pdf"
    with open(pdf_path, "wb") as f:
        writer.write(f)
    assert isinstance(writer.pages[0].mediabox, RectangleObject)
    return pdf_path


def test_load_pdf_returns_document(sample_pdf: Path):
    doc = load_pdf(sample_pdf)
    assert doc.metadata["filetype"] == "pdf"
    assert doc.metadata["num_pages"] == 2
    assert doc.metadata["source"] == "sample.pdf"
    assert isinstance(doc.text, str)


def test_load_dispatches_by_extension(sample_pdf: Path):
    doc = load(sample_pdf)
    assert doc.metadata["filetype"] == "pdf"


def test_load_rejects_unknown_extension(tmp_path: Path):
    weird = tmp_path / "notes.xyz"
    weird.write_text("hello")
    with pytest.raises(UnsupportedFormatError):
        load(weird)
