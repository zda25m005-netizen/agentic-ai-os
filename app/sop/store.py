"""SOP document + version persistence (server-side SQLite)."""

from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path

from app.sop.models import SopDoc, SopVersion

DB_PATH = Path("sop_store.db")  # overridable in tests


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS sop_doc (id TEXT PRIMARY KEY, data TEXT, created_at REAL, updated_at REAL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS sop_version "
        "(id TEXT PRIMARY KEY, doc_id TEXT, label TEXT, content TEXT, created_at REAL)"
    )
    return conn


def create(doc: SopDoc) -> SopDoc:
    now = time.time()
    doc.id = doc.id or f"sop-{uuid.uuid4().hex[:12]}"
    doc.created_at, doc.updated_at = now, now
    with _conn() as conn:
        conn.execute(
            "INSERT INTO sop_doc (id, data, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (doc.id, doc.model_dump_json(), now, now),
        )
    return doc


def get(doc_id: str) -> SopDoc | None:
    with _conn() as conn:
        row = conn.execute("SELECT data FROM sop_doc WHERE id=?", (doc_id,)).fetchone()
    return SopDoc.model_validate_json(row[0]) if row else None


def update(doc: SopDoc) -> SopDoc:
    doc.updated_at = time.time()
    with _conn() as conn:
        conn.execute(
            "UPDATE sop_doc SET data=?, updated_at=? WHERE id=?",
            (doc.model_dump_json(), doc.updated_at, doc.id),
        )
    return doc


def list_docs() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT data FROM sop_doc ORDER BY updated_at DESC").fetchall()
    out = []
    for (data,) in rows:
        d = SopDoc.model_validate_json(data)
        out.append(
            {
                "id": d.id,
                "title": d.title,
                "target": d.target.model_dump(),
                "updated_at": d.updated_at,
                "words": len(d.content.split()),
            }
        )
    return out


def delete(doc_id: str) -> bool:
    with _conn() as conn:
        conn.execute("DELETE FROM sop_version WHERE doc_id=?", (doc_id,))
        return conn.execute("DELETE FROM sop_doc WHERE id=?", (doc_id,)).rowcount > 0


def add_version(doc_id: str, label: str, content: str) -> SopVersion:
    v = SopVersion(
        id=f"v-{uuid.uuid4().hex[:10]}",
        doc_id=doc_id,
        label=label,
        content=content,
        created_at=time.time(),
    )
    with _conn() as conn:
        conn.execute(
            "INSERT INTO sop_version (id, doc_id, label, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (v.id, v.doc_id, v.label, v.content, v.created_at),
        )
    return v


def list_versions(doc_id: str) -> list[SopVersion]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, doc_id, label, content, created_at FROM sop_version WHERE doc_id=? ORDER BY created_at DESC",
            (doc_id,),
        ).fetchall()
    return [
        SopVersion(id=r[0], doc_id=r[1], label=r[2], content=r[3], created_at=r[4]) for r in rows
    ]


def get_version(vid: str) -> SopVersion | None:
    with _conn() as conn:
        r = conn.execute(
            "SELECT id, doc_id, label, content, created_at FROM sop_version WHERE id=?", (vid,)
        ).fetchone()
    return (
        SopVersion(id=r[0], doc_id=r[1], label=r[2], content=r[3], created_at=r[4]) if r else None
    )
