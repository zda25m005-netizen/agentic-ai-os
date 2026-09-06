"""SOP Builder: docs, target import, generation grounding, fact-check, quality, versions, export."""

import asyncio

from app.sop import export as sop_export
from app.sop import factcheck, quality, store
from app.sop.generate import generate
from app.sop.models import SopDoc, SopRequirements, SopTarget


def _fresh(tmp_path):
    store.DB_PATH = tmp_path / "sop.db"


# --- documents + versions ---------------------------------------------------
def test_create_get_update(tmp_path):
    _fresh(tmp_path)
    doc = store.create(SopDoc(id="", title="Test"))
    assert doc.id and store.get(doc.id).title == "Test"
    doc.content = "Hello"
    store.update(doc)
    assert store.get(doc.id).content == "Hello"


def test_versions_snapshot_and_restore(tmp_path):
    _fresh(tmp_path)
    doc = store.create(SopDoc(id="", content="v1"))
    store.add_version(doc.id, "Draft 1", "v1")
    doc.content = "v2"
    store.update(doc)
    vs = store.list_versions(doc.id)
    assert len(vs) == 1 and vs[0].content == "v1"
    v = store.get_version(vs[0].id)
    assert v.content == "v1"


# --- grounded generation (fake LLM) -----------------------------------------
def test_generate_uses_facts_and_no_fabrication(tmp_path):
    _fresh(tmp_path)
    seen = {}

    async def fake(messages):
        seen["user"] = messages[1]["content"]
        seen["sys"] = messages[0]["content"]
        return "I hold an M.Tech and have worked with Python."

    doc = SopDoc(id="d", target=SopTarget(university="ETH Zurich", field="Artificial Intelligence"))
    profile = {"degree": "master", "field": "Artificial Intelligence", "gpa": 8.7}
    resume = {"skills": ["Python", "PyTorch"], "education": ["M.Tech in AI"]}
    out = asyncio.run(generate(doc, profile, resume, fake))
    assert "M.Tech" in out
    assert "ETH Zurich" in seen["user"] and "Python" in seen["user"]
    assert "never invent" in seen["sys"].lower() or "not invent" in seen["sys"].lower()


# --- fact check -------------------------------------------------------------
def test_factcheck_flags_unsupported_and_verifies_skills():
    content = "I am proficient in Python. I published a paper on GANs. My GPA is excellent."
    profile = {"degree": "master"}  # no gpa
    resume = {"skills": ["Python"]}  # no publications
    r = factcheck.check(content, profile, resume)
    kinds = {c.text: c.status for c in r.claims}
    assert any(s == "verified" for s in kinds.values())  # Python
    assert r.needs_verification >= 2  # publication + GPA


def test_factcheck_placeholder_is_unsupported():
    r = factcheck.check("My research on [Information needed: project] is strong.", {}, {})
    assert r.unsupported >= 1


# --- quality ----------------------------------------------------------------
def test_quality_wordcount_limit_and_generic():
    content = "I am passionate about research. " * 3 + "I studied at university and did research."
    q = quality.analyze(content, SopRequirements(word_limit=5))
    assert q.word_count > 5 and q.over_limit is True
    assert "passionate" in q.generic_flags
    assert any(c["section"] == "Academic background" for c in q.coverage)


def test_quality_coverage_and_repetition():
    q = quality.analyze(
        "My motivation is clear. My motivation is clear. Career goal is a PhD.", SopRequirements()
    )
    assert q.repetition_flags  # repeated sentence detected


# --- export -----------------------------------------------------------------
def test_export_txt_docx_pdf():
    doc = SopDoc(
        id="d",
        title="My SOP",
        content="First paragraph.\n\nSecond paragraph with **bold** removed.",
    )
    txt, m1, f1 = sop_export.export(doc, "txt")
    assert b"First paragraph" in txt and "**" not in txt.decode() and f1.endswith(".txt")
    docx_bytes, m2, f2 = sop_export.export(doc, "docx")
    assert len(docx_bytes) > 500 and f2.endswith(".docx")
    pdf_bytes, m3, f3 = sop_export.export(doc, "pdf")
    assert pdf_bytes[:4] == b"%PDF" and f3.endswith(".pdf")


def test_export_strips_markdown():
    doc = SopDoc(id="d", content="## Heading\n**bold** and *italic* text")
    assert (
        "##" not in sop_export.to_txt(doc).decode() and "**" not in sop_export.to_txt(doc).decode()
    )
