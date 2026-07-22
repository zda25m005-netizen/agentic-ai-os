"""Scorers for the RAG evaluation harness.

Each scorer returns a float in [0, 1] for one Q&A item; the runner (Day 21)
averages them across the dataset to produce the headline metrics.

Metrics:
  - recall_at_k:        did the gold source appear in the top-k retrieved?
  - answer_match:       fast, deterministic substring check (no API cost)
  - llm_judge:          semantic correctness via an LLM judge (async)
  - citation_accuracy:  did the answer cite the gold source?
"""
from __future__ import annotations

import re
from collections.abc import Awaitable, Callable

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]")


def normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = _PUNCT_RE.sub(" ", text.lower())
    return _WS_RE.sub(" ", text).strip()


def recall_at_k(retrieved_sources: list[str], expected_source: str, k: int = 5) -> float:
    """1.0 if the gold source is within the top-k retrieved sources."""
    return 1.0 if expected_source in retrieved_sources[:k] else 0.0


def answer_match(expected: str, actual: str) -> float:
    """1.0 if the normalized expected answer is contained in the actual answer.

    A cheap correctness proxy — good for short factual answers, and free.
    """
    exp = normalize(expected)
    act = normalize(actual)
    if not exp:
        return 0.0
    return 1.0 if exp in act else 0.0


def citation_accuracy(cited_sources: list[str], expected_source: str) -> float:
    """1.0 if the answer cited the gold source at all."""
    return 1.0 if expected_source in cited_sources else 0.0


_JUDGE_PROMPT = (
    "You are grading an answer. Reply with exactly 'YES' if the candidate "
    "answer is correct given the reference answer, otherwise 'NO'.\n\n"
    "Question: {q}\nReference answer: {ref}\nCandidate answer: {cand}\n\n"
    "Grade (YES or NO):"
)

# A judge is any async function taking chat messages and returning text.
JudgeFn = Callable[[list[dict]], Awaitable[str]]


async def llm_judge(
    question: str,
    expected: str,
    actual: str,
    judge: JudgeFn,
) -> float:
    """Ask an LLM judge whether `actual` is correct vs `expected`. Returns 1/0."""
    prompt = _JUDGE_PROMPT.format(q=question, ref=expected, cand=actual)
    verdict = await judge([{"role": "user", "content": prompt}])
    return 1.0 if "yes" in verdict.strip().lower()[:5] else 0.0
