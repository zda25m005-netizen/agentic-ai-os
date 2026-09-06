"""Durable store for rich MemoryRecords (SQLite; server-side, per-owner isolated).

Superseded/archived records are retained (never hard-deleted) so temporal reasoning
can still see history. Indexed columns support fast filtering by owner/layer/status/key.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.memory.records import MemoryRecord

DB_PATH = Path("memory_store.db")  # overridable in tests


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS memory ("
        "id TEXT PRIMARY KEY, owner TEXT, memory_type TEXT, status TEXT, key TEXT, "
        "mission_id INTEGER, updated_at REAL, data TEXT)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_owner ON memory(owner, status)")
    return conn


def _save(conn: sqlite3.Connection, r: MemoryRecord) -> None:
    conn.execute(
        "INSERT INTO memory (id, owner, memory_type, status, key, mission_id, updated_at, data) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
        "owner=excluded.owner, memory_type=excluded.memory_type, status=excluded.status, "
        "key=excluded.key, mission_id=excluded.mission_id, updated_at=excluded.updated_at, "
        "data=excluded.data",
        (
            r.id,
            r.owner,
            r.memory_type,
            r.status,
            r.key,
            r.mission_id,
            r.updated_at,
            r.model_dump_json(),
        ),
    )


def put(r: MemoryRecord) -> MemoryRecord:
    with _conn() as conn:
        _save(conn, r)
    return r


def get(mem_id: str, owner: str = "me") -> MemoryRecord | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT data FROM memory WHERE id=? AND owner=?", (mem_id, owner)
        ).fetchone()
    return MemoryRecord.model_validate_json(row[0]) if row else None


def query(
    owner: str = "me",
    *,
    layer: str | None = None,
    status: str | None = None,
    include_archived: bool = False,
) -> list[MemoryRecord]:
    sql = "SELECT data FROM memory WHERE owner=?"
    args: list = [owner]
    if layer:
        sql += " AND memory_type=?"
        args.append(layer)
    if status:
        sql += " AND status=?"
        args.append(status)
    elif not include_archived:
        sql += " AND status NOT IN ('archived')"
    sql += " ORDER BY updated_at DESC"
    with _conn() as conn:
        rows = conn.execute(sql, args).fetchall()
    return [MemoryRecord.model_validate_json(r[0]) for r in rows]


def find_all_by_key(owner: str, layer: str, key: str) -> list[MemoryRecord]:
    """All currently-active records holding this single-value key."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT data FROM memory WHERE owner=? AND memory_type=? AND key=? "
            "AND status NOT IN ('superseded','archived') ORDER BY updated_at DESC",
            (owner, layer, key),
        ).fetchall()
    return [MemoryRecord.model_validate_json(r[0]) for r in rows]


def find_by_key(owner: str, layer: str, key: str) -> MemoryRecord | None:
    recs = find_all_by_key(owner, layer, key)
    return recs[0] if recs else None


def delete_hard(mem_id: str, owner: str = "me") -> bool:
    """Physical delete — only for user-requested erasure, not for supersession."""
    with _conn() as conn:
        return (
            conn.execute("DELETE FROM memory WHERE id=? AND owner=?", (mem_id, owner)).rowcount > 0
        )
