"""DPO dataset builder + exporter tests."""
import json
from dataclasses import dataclass

from app.feedback import dpo
from app.feedback.dpo_export import export_jsonl, to_trl


@dataclass
class _FB:
    query: str
    answer: str
    rating: str
    better_answer: str | None = None


# --- preference pairs ---

def test_down_with_better_answer_makes_pair():
    items = [_FB("q1", "meh answer", "down", better_answer="great answer")]
    pairs = dpo.build_preference_pairs(items)
    assert len(pairs) == 1
    assert pairs[0].chosen == "great answer"
    assert pairs[0].rejected == "meh answer"


def test_up_and_down_same_query_makes_pair():
    items = [_FB("q", "good", "up"), _FB("q", "bad", "down")]
    pairs = dpo.build_preference_pairs(items)
    assert any(p.chosen == "good" and p.rejected == "bad" for p in pairs)


def test_invalid_and_duplicate_pairs_dropped():
    items = [
        _FB("q", "same", "down", better_answer="same"),   # chosen==rejected -> drop
        _FB("q2", "a", "down", better_answer="b"),
        _FB("q2", "a", "down", better_answer="b"),          # duplicate -> drop
    ]
    pairs = dpo.build_preference_pairs(items)
    assert len(pairs) == 1
    assert pairs[0].prompt == "q2"


# --- validation + stats ---

def test_validate_flags_bad_pairs():
    bad = [dpo.PreferencePair(prompt="", chosen="x", rejected="y"),
           dpo.PreferencePair(prompt="p", chosen="z", rejected="z")]
    issues = dpo.validate_pairs(bad)
    assert any("empty prompt" in i for i in issues)
    assert any("chosen == rejected" in i for i in issues)


def test_dataset_stats():
    pairs = [dpo.PreferencePair("p1", "chosen", "no"),
             dpo.PreferencePair("p2", "chosen2", "nope")]
    stats = dpo.dataset_stats(pairs)
    assert stats["n_pairs"] == 2
    assert stats["n_prompts"] == 2


# --- export ---

def test_to_trl_format():
    row = to_trl(dpo.PreferencePair("p", "c", "r"))
    assert row == {"prompt": "p", "chosen": "c", "rejected": "r"}


def test_export_jsonl_roundtrip(tmp_path):
    pairs = [dpo.PreferencePair("p1", "c1", "r1"), dpo.PreferencePair("p2", "c2", "r2")]
    out = tmp_path / "dpo.jsonl"
    n = export_jsonl(pairs, out)
    assert n == 2
    lines = out.read_text().strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert set(first.keys()) == {"prompt", "chosen", "rejected"}
    assert first["chosen"] == "c1"
