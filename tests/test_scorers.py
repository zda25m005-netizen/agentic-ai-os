from eval import scorers


def test_normalize_strips_punct_and_case():
    assert scorers.normalize("  AES-256!  ") == "aes 256"


def test_recall_at_k():
    retrieved = ["a.pdf", "b.pdf", "c.pdf"]
    assert scorers.recall_at_k(retrieved, "b.pdf", k=3) == 1.0
    assert scorers.recall_at_k(retrieved, "b.pdf", k=1) == 0.0
    assert scorers.recall_at_k(retrieved, "z.pdf", k=3) == 0.0


def test_answer_match_substring_and_normalization():
    assert scorers.answer_match("12%", "Revenue grew 12% year over year.") == 1.0
    assert scorers.answer_match("AES-256", "Encrypted with aes 256 at rest.") == 1.0
    assert scorers.answer_match("Python", "The language is Java.") == 0.0
    assert scorers.answer_match("", "anything") == 0.0


def test_citation_accuracy():
    assert scorers.citation_accuracy(["q3.pdf", "hr.docx"], "q3.pdf") == 1.0
    assert scorers.citation_accuracy(["hr.docx"], "q3.pdf") == 0.0
    assert scorers.citation_accuracy([], "q3.pdf") == 0.0


async def test_llm_judge_yes():
    async def judge(messages):
        return "YES"

    score = await scorers.llm_judge("Q?", "Paris", "The capital is Paris.", judge)
    assert score == 1.0


async def test_llm_judge_no():
    async def judge(messages):
        return "NO, incorrect."

    score = await scorers.llm_judge("Q?", "Paris", "London.", judge)
    assert score == 0.0


async def test_llm_judge_receives_prompt():
    captured = {}

    async def judge(messages):
        captured["content"] = messages[0]["content"]
        return "YES"

    await scorers.llm_judge("What city?", "Paris", "Paris.", judge)
    assert "Reference answer: Paris" in captured["content"]
    assert "Candidate answer: Paris." in captured["content"]
