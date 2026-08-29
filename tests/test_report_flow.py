"""Evidence-first report flow: constrained LLM synthesis over the artifact."""
import json

from app.analysis.report_flow import build_report_evidence_first
from app.exec.pdf import is_valid_pdf
from app.exec.report_pdf import render_report
from app.missions.models import Mission, Task
from app.missions.state import MissionStatus, TaskStatus


def _task(i, d, r):
    return Task(id=i, mission_id=1, description=d, status=TaskStatus.DONE,
                depends_on=[], result=r, created_at=0.0, updated_at=0.0)


def _mission():
    return Mission(id=1, objective="Compare RAG vs Fine-tuning", status=MissionStatus.COMPLETED,
                   priority=0, deadline=None, created_at=0.0, updated_at=0.0, meta={})


_TASKS = [
    _task(1, "RAG", "RAG retrieves external documents at query time. It keeps knowledge "
          "fresh without retraining. Sources:\nhttps://arxiv.org/abs/2005.11401\n"
          "https://en.wikipedia.org/wiki/Retrieval-augmented_generation"),
    _task(2, "Fine-tuning", "Fine-tuning bakes knowledge into model weights. "
          "Sources:\nhttps://en.wikipedia.org/wiki/Fine-tuning_(deep_learning)"),
]


async def test_flow_without_llm_is_valid_and_grounded():
    r = await build_report_evidence_first(_mission(), _TASKS, chat_fn=None)
    assert r.findings and all(f.confidence for f in r.findings)
    # every finding stating a figure must be source-backed (validator guarantee)
    assert r.limitations
    assert is_valid_pdf(render_report(r))


async def test_llm_synthesis_only_adds_prose_over_findings():
    captured = {}

    async def fake_chat(messages):
        captured["system"] = messages[0]["content"]
        # respond with reasoning keyed to a real finding id + prose fields
        return json.dumps({
            "executive_summary": "RAG suits fresh recall; fine-tuning changes behaviour.",
            "recommendation": "Use RAG for freshness, fine-tuning for behaviour change.",
            "reasoning": [{"finding_id": "F1", "interpretation": "Retrieval grounds answers.",
                           "implication": "Prefer RAG where facts change."}],
        })

    r = await build_report_evidence_first(_mission(), _TASKS, chat_fn=fake_chat)
    assert "research writer" in captured["system"].lower()
    assert r.executive_summary.startswith("RAG suits fresh")
    assert r.recommendation.startswith("Use RAG")
    # the interpretation/implication were merged into the grounded finding body
    joined = " ".join(f.body for f in r.findings)
    assert "Retrieval grounds answers" in joined


async def test_bad_llm_response_falls_back_to_deterministic():
    async def bad(messages):
        return "not json at all"

    r = await build_report_evidence_first(_mission(), _TASKS, chat_fn=bad)
    assert r.findings and r.executive_summary          # deterministic summary used
    assert is_valid_pdf(render_report(r))
