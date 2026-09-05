"""Saved scholarships — server-side persistence (SQLite, not the browser)."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path("scholarship_store.db")  # overridable in tests


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS saved_scholarship ("
        "id TEXT PRIMARY KEY, saved_at REAL, status TEXT, data TEXT)"
    )
    return conn


def save(scholarship: dict, status: str = "Interested") -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO saved_scholarship (id, saved_at, status, data) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET status=excluded.status, data=excluded.data",
            (scholarship["id"], time.time(), status, json.dumps(scholarship)),
        )


def list_saved() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT data, saved_at, status FROM saved_scholarship ORDER BY saved_at DESC"
        ).fetchall()
    out = []
    for data, saved_at, status in rows:
        d = json.loads(data)
        d["saved_at"] = saved_at
        d["tracking_status"] = status
        out.append(d)
    return out


def set_status(scholarship_id: str, status: str) -> bool:
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE saved_scholarship SET status=? WHERE id=?", (status, scholarship_id)
        )
        return cur.rowcount > 0


def remove(scholarship_id: str) -> bool:
    with _conn() as conn:
        cur = conn.execute("DELETE FROM saved_scholarship WHERE id=?", (scholarship_id,))
        return cur.rowcount > 0
