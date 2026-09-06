"""Saved PhD opportunities — server-side SQLite (not the browser)."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path("phd_store.db")  # overridable in tests


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS saved_phd (id TEXT PRIMARY KEY, saved_at REAL, status TEXT, notes TEXT, data TEXT)"
    )
    return conn


def save(opp: dict, status: str = "Interested", notes: str = "") -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO saved_phd (id, saved_at, status, notes, data) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET status=excluded.status, notes=excluded.notes, data=excluded.data",
            (opp["id"], time.time(), status, notes, json.dumps(opp)),
        )


def list_saved() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT data, saved_at, status, notes FROM saved_phd ORDER BY saved_at DESC"
        ).fetchall()
    out = []
    for data, saved_at, status, notes in rows:
        d = json.loads(data)
        d["saved_at"], d["tracking_status"], d["notes"] = saved_at, status, notes
        out.append(d)
    return out


def set_status(pid: str, status: str) -> bool:
    with _conn() as conn:
        return conn.execute("UPDATE saved_phd SET status=? WHERE id=?", (status, pid)).rowcount > 0


def remove(pid: str) -> bool:
    with _conn() as conn:
        return conn.execute("DELETE FROM saved_phd WHERE id=?", (pid,)).rowcount > 0
