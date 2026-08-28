"""Local PDF generation + validation + the mission report download endpoint."""
import pytest
from httpx import ASGITransport, AsyncClient

import app.missions.models  # noqa: F401  (register tables)
from app.api import missions as mapi
from app.api.main import app
from app.db import session as db
from app.exec.pdf import PdfDoc, Section, build_pdf, is_valid_pdf, page_count
from app.missions.repository import MissionRepository
from app.missions.state import TaskStatus

SQLITE_MEMORY = "sqlite+aiosqlite:///:memory:"


# --- pdf writer ---

def test_build_pdf_is_valid():
    pdf = build_pdf(PdfDoc("Report", [Section("Intro", "Hello world.")]))
    assert is_valid_pdf(pdf)
    assert pdf.startswith(b"%PDF-") and pdf.rstrip().endswith(b"%%EOF")
    assert page_count(pdf) >= 1


def test_pdf_escapes_special_chars():
    pdf = build_pdf(PdfDoc("T", [Section("H", "parens (x) and back\\slash")]))
    assert is_valid_pdf(pdf)  # must not corrupt the stream


def test_long_content_paginates():
    body = "\n".join(f"line {i} with some words to wrap across the page" for i in range(200))
    pdf = build_pdf(PdfDoc("Big", [Section("Body", body)]))
    assert is_valid_pdf(pdf)
    assert page_count(pdf) >= 2  # spilled onto multiple pages


def test_invalid_pdf_rejected():
    assert not is_valid_pdf(b"not a pdf")
    assert not is_valid_pdf(b"%PDF- but no eof marker")


# --- endpoint ---

@pytest.fixture
async def client():
    engine = db.get_engine(SQLITE_MEMORY)
    await db.init_models(engine)
    repo = MissionRepository(db.get_sessionmaker(engine))
    app.dependency_overrides[mapi.get_mission_repo] = lambda: repo
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c, repo
    app.dependency_overrides.clear()
    await engine.dispose()


async def test_report_endpoint_returns_valid_pdf(client):
    c, repo = client
    m = await repo.create("Compare A and B")
    t = await repo.add_task(m.id, "research A", depends_on=[])
    await repo.set_task_status(t.id, TaskStatus.DONE, result="A is fast")

    r = await c.get(f"/missions/{m.id}/report.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"]
    assert is_valid_pdf(r.content)


async def test_report_404_for_unknown_mission(client):
    c, _ = client
    assert (await c.get("/missions/9999/report.pdf")).status_code == 404
