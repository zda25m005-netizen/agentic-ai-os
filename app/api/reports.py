"""Generic report generation — turn any content into a downloadable PDF.

Used by the Playground to export an agent/RAG answer, and reusable by any client.
Content is provided in the request (not persisted), so it works for ephemeral
results too. Real local PDF via app.exec.pdf (no external API).
"""
from __future__ import annotations

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from app.exec.pdf import PdfDoc, Section, build_pdf

router = APIRouter(prefix="/reports", tags=["reports"])


class SectionIn(BaseModel):
    heading: str
    body: str = ""


class ReportIn(BaseModel):
    title: str = "Report"
    filename: str = "report"
    sections: list[SectionIn] = Field(default_factory=list)


@router.post("/pdf")
def report_pdf(req: ReportIn) -> Response:
    """Build a PDF from provided title + sections and return it as a download."""
    doc = PdfDoc(title=req.title, sections=[Section(s.heading, s.body) for s in req.sections])
    safe = "".join(c for c in req.filename if c.isalnum() or c in "-_") or "report"
    return Response(
        content=build_pdf(doc), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe}.pdf"'},
    )
