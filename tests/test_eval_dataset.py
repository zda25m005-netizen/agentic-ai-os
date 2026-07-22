import pytest

from eval import dataset


def test_corpus_loads():
    corpus = dataset.load_corpus()
    assert len(corpus) >= 5
    assert all(d.source and d.text for d in corpus)


def test_qa_loads():
    qa = dataset.load_qa()
    assert len(qa) >= 15
    assert all(item.question and item.expected_answer for item in qa)


def test_dataset_is_internally_consistent():
    # Every gold source must exist in the corpus, and ids unique.
    dataset.validate(dataset.load_qa(), dataset.load_corpus())


def test_validate_rejects_dangling_source():
    corpus = [dataset.CorpusDoc(source="a.pdf", text="x")]
    qa = [dataset.QAItem("q1", "?", "ans", "missing.pdf")]
    with pytest.raises(ValueError, match="not in corpus"):
        dataset.validate(qa, corpus)


def test_validate_rejects_duplicate_ids():
    corpus = [dataset.CorpusDoc(source="a.pdf", text="x")]
    qa = [
        dataset.QAItem("q1", "?", "ans", "a.pdf"),
        dataset.QAItem("q1", "?", "ans", "a.pdf"),
    ]
    with pytest.raises(ValueError, match="duplicate"):
        dataset.validate(qa, corpus)
