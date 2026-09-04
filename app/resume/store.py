"""Persist the candidate's parsed resume profile (single active profile).

Server-side storage (a small SQLite file), never the browser. Only the parsed,
structured profile + filename + timestamp are stored — never the raw resume
bytes, keeping personal document contents off disk.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path("resume_store.db")  # overridable in tests
_OWNER = "me"  # single-user local app


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS resume_profile ("
        "owner TEXT PRIMARY KEY, filename TEXT, uploaded_at REAL, profile TEXT)"
    )
    return conn


def save_profile(profile: dict, filename: str) -> dict:
    rec = {"filename": filename, "uploaded_at": time.time(), "profile": profile}
    with _conn() as conn:
        conn.execute(
            "INSERT INTO resume_profile (owner, filename, uploaded_at, profile) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(owner) DO UPDATE SET "
            "filename=excluded.filename, uploaded_at=excluded.uploaded_at, "
            "profile=excluded.profile",
            (_OWNER, filename, rec["uploaded_at"], json.dumps(profile)),
        )
    return rec


def load_profile() -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT filename, uploaded_at, profile FROM resume_profile WHERE owner=?", (_OWNER,)
        ).fetchone()
    if not row:
        return None
    return {"filename": row[0], "uploaded_at": row[1], "profile": json.loads(row[2])}


def delete_profile() -> bool:
    with _conn() as conn:
        cur = conn.execute("DELETE FROM resume_profile WHERE owner=?", (_OWNER,))
        return cur.rowcount > 0
