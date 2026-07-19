import pytest

from app.rag.chunker import chunk_text


def test_short_text_single_chunk():
    chunks = chunk_text("Hello world.", chunk_size=100, overlap=10)
    assert len(chunks) == 1
    assert chunks[0].text == "Hello world."
    assert chunks[0].index == 0


def test_empty_text_returns_no_chunks():
    assert chunk_text("   ", chunk_size=100, overlap=10) == []


def test_respects_chunk_size():
    text = " ".join(f"word{i}" for i in range(500))
    chunks = chunk_text(text, chunk_size=200, overlap=20)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c.text) <= 200 + 21  # size + carried overlap + newline


def test_prefers_paragraph_boundaries():
    para_a = "First paragraph. " * 5
    para_b = "Second paragraph. " * 5
    text = f"{para_a.strip()}\n\n{para_b.strip()}"
    chunks = chunk_text(text, chunk_size=len(para_a) + 10, overlap=0)
    assert len(chunks) == 2
    assert chunks[0].text.startswith("First paragraph.")
    assert chunks[1].text.startswith("Second paragraph.")


def test_overlap_carries_context():
    text = "\n\n".join(f"Paragraph number {i}. " * 4 for i in range(10))
    chunks = chunk_text(text, chunk_size=300, overlap=50)
    assert len(chunks) > 2
    # Tail of chunk N appears at the head of chunk N+1.
    tail = chunks[0].text[-30:]
    assert tail.strip()[:15] in chunks[1].text[:100]


def test_metadata_copied_to_all_chunks():
    text = " ".join("meta test." for _ in range(200))
    chunks = chunk_text(text, chunk_size=150, overlap=10, metadata={"source": "x.pdf"})
    assert all(c.metadata == {"source": "x.pdf"} for c in chunks)
    # Each chunk owns an independent dict.
    chunks[0].metadata["mutated"] = True
    assert "mutated" not in chunks[1].metadata


def test_indexes_are_sequential():
    text = " ".join(f"w{i}" for i in range(1000))
    chunks = chunk_text(text, chunk_size=100, overlap=10)
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        chunk_text("abc", chunk_size=0)
    with pytest.raises(ValueError):
        chunk_text("abc", chunk_size=100, overlap=100)
