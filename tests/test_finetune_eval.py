"""Before/after eval tests — fake generators, no torch."""
from eval import finetune_eval as fe
from eval import finetune_runner

# --- format adherence ---

def test_format_adherence_rewards_clean_concise():
    assert fe.format_adherence("Paris.") == 1.0
    assert fe.format_adherence("") == 0.0
    assert fe.format_adherence("```python\nprint(1)\n```") == 0.0  # code fence
    assert fe.format_adherence("word " * 100) == 0.5               # too long


# --- evaluate / compare ---

def _items():
    return [("What is 2+2?", "4"), ("Capital of France?", "Paris")]


def test_evaluate_scores_a_model():
    def perfect(instruction):
        return {"What is 2+2?": "4", "Capital of France?": "Paris"}[instruction]

    result = fe.evaluate(_items(), perfect)
    assert result["n"] == 2
    assert result["exact_match"] == 1.0
    assert result["format_adherence"] == 1.0


def test_compare_base_vs_finetuned():
    def base(_i):
        return "I am not sure about that, but here is a very long rambling answer " * 3

    def finetuned(instruction):
        return {"What is 2+2?": "4", "Capital of France?": "Paris"}[instruction]

    results = fe.compare(_items(), base, finetuned)
    assert results["finetuned"]["exact_match"] > results["base"]["exact_match"]


def test_format_comparison_table():
    results = {
        "base": {"exact_match": 0.5, "format_adherence": 0.5},
        "finetuned": {"exact_match": 1.0, "format_adherence": 1.0},
    }
    table = fe.format_comparison_table(results)
    assert "Base" in table and "Fine-tuned" in table
    assert "100%" in table and "50%" in table


# --- held-out loader + runner import ---

def test_load_heldout_returns_pairs():
    items = fe.load_heldout()
    assert len(items) >= 1
    assert all(len(pair) == 2 and pair[0] and pair[1] for pair in items)


def test_runner_imports_without_torch():
    assert callable(finetune_runner.hf_generate_fn)
    assert callable(finetune_runner.main)
