"""SFT dataset assembly / formatting / split tests."""
import json
from pathlib import Path

from app.finetune import dataset
from app.finetune import format as fmt
from app.finetune.build_dataset import write_jsonl
from app.finetune.dataset import SFTExample

ROOT = Path(__file__).resolve().parents[1]


# --- assembly ---

def test_from_qa_reads_real_dataset():
    examples = dataset.from_qa()
    assert len(examples) >= 10
    assert all(e.instruction and e.output and e.source == "qa" for e in examples)


def test_build_examples_dedupes_by_instruction(tmp_path):
    qa = tmp_path / "qa.json"
    gqa = tmp_path / "gqa.json"
    qa.write_text(json.dumps([
        {"question": "What is X?", "expected_answer": "A"},
        {"question": "What is X?", "expected_answer": "A dup"},
    ]))
    gqa.write_text(json.dumps([
        {"question": "How are A and B related?", "expected_facts": ["A", "B"]},
    ]))
    ex = dataset.build_examples(qa_path=qa, graph_qa_path=gqa)
    instructions = [e.instruction for e in ex]
    assert instructions.count("What is X?") == 1
    assert any(e.source == "graph_qa" for e in ex)


# --- formatting ---

def test_to_chat_shape():
    row = fmt.to_chat(SFTExample("q?", "a.", "qa"))
    roles = [m["role"] for m in row["messages"]]
    assert roles == ["system", "user", "assistant"]
    assert row["messages"][1]["content"] == "q?"
    assert row["messages"][2]["content"] == "a."


# --- split ---

def test_train_val_split_is_deterministic_and_partitions():
    ex = [SFTExample(f"q{i}", f"a{i}", "qa") for i in range(10)]
    tr1, va1 = fmt.train_val_split(ex, val_frac=0.2, seed=42)
    tr2, va2 = fmt.train_val_split(ex, val_frac=0.2, seed=42)
    assert [e.instruction for e in tr1] == [e.instruction for e in tr2]  # deterministic
    assert len(tr1) + len(va1) == 10
    assert len(va1) == 2 and len(tr1) == 8
    # disjoint
    assert not ({e.instruction for e in tr1} & {e.instruction for e in va1})


def test_split_handles_tiny_input():
    assert fmt.train_val_split([]) == ([], [])
    tr, va = fmt.train_val_split([SFTExample("q", "a", "qa")])
    assert len(tr) == 1 and len(va) == 0


# --- write + dataset card ---

def test_write_jsonl_roundtrip(tmp_path):
    rows = [fmt.to_chat(SFTExample("q", "a", "qa"))]
    n = write_jsonl(rows, tmp_path / "train.jsonl")
    assert n == 1
    line = json.loads((tmp_path / "train.jsonl").read_text().strip())
    assert line["messages"][2]["content"] == "a"


def test_dataset_card_exists_and_documents_sources():
    card = (ROOT / "app/finetune/DATASET_CARD.md").read_text()
    assert "qa.json" in card and "graph_qa.json" in card
    assert "License" in card
