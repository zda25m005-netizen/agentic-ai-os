from pathlib import Path

import pytest
from docx import Document as DocxDocument

from app.rag import cli, embeddings, vectorstore


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    async def fake_embed(texts):
        return [[float(len(t)), 1.0, 0.0, -1.0] for t in texts]

    monkeypatch.setattr(embeddings, "embed", fake_embed)


@pytest.fixture(autouse=True)
def in_memory_client(monkeypatch):
    client = vectorstore.get_client(location=":memory:")
    monkeypatch.setattr(vectorstore, "get_client", lambda *a, **k: client)
    return client


def _make_docx(path: Path, n: int = 20) -> None:
    d = DocxDocument()
    for i in range(n):
        d.add_paragraph(f"Line {i} about revenue, strategy and operations.")
    d.save(path)


def test_expand_paths_file_and_dir(tmp_path: Path):
    _make_docx(tmp_path / "a.docx")
    (tmp_path / "sub").mkdir()
    _make_docx(tmp_path / "sub" / "b.docx")
    (tmp_path / "ignore.txt").write_text("nope")

    found = cli.expand_paths([str(tmp_path)])
    names = sorted(f.name for f in found)
    assert names == ["a.docx", "b.docx"]


def test_main_ingests_directory(tmp_path: Path, in_memory_client, capsys):
    _make_docx(tmp_path / "report.docx")

    rc = cli.main(["ingest", str(tmp_path), "--collection", "kb"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ingested report.docx" in out
    assert in_memory_client.collection_exists("kb")


def test_main_no_files_returns_error(tmp_path: Path, capsys):
    rc = cli.main(["ingest", str(tmp_path / "missing")])
    assert rc == 1
    assert "no supported files" in capsys.readouterr().err
