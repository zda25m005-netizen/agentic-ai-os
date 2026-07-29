"""Episodic memory: a persistent log of past agent runs.

Every completed task (goal + final answer) is saved so the system has a
history it can review, search, and later recall semantically (Day 39).
Backed by SQLite (stdlib) so it persists across restarts with no server;
point MEMORY_DB_PATH at a file to keep it, or use ':memory:' for ephemeral.
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass


@dataclass
class Episode:
    """One recorded agent run."""

    id: int
    goal: str
    answer: str
    ts: float


class EpisodicMemory:
    """SQLite-backed store of agent runs."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._init_schema()

    @classmethod
    def open(cls, path: str = ":memory:") -> EpisodicMemory:
        conn = sqlite3.connect(path)
        return cls(conn)

    def _init_schema(self) -> None:
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS episodes ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  goal TEXT NOT NULL,"
            "  answer TEXT NOT NULL,"
            "  ts REAL NOT NULL)"
        )
        self._conn.commit()

    def save(self, goal: str, answer: str, ts: float | None = None) -> int:
        """Record a run; return its id."""
        ts = time.time() if ts is None else ts
        cur = self._conn.execute(
            "INSERT INTO episodes (goal, answer, ts) VALUES (?, ?, ?)",
            (goal, answer, ts),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def _row(self, r: tuple) -> Episode:
        return Episode(id=r[0], goal=r[1], answer=r[2], ts=r[3])

    def recent(self, limit: int = 10) -> list[Episode]:
        """Most recent runs, newest first."""
        rows = self._conn.execute(
            "SELECT id, goal, answer, ts FROM episodes ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row(r) for r in rows]

    def search(self, term: str, limit: int = 10) -> list[Episode]:
        """Keyword search over goals and answers (newest first)."""
        like = f"%{term}%"
        rows = self._conn.execute(
            "SELECT id, goal, answer, ts FROM episodes "
            "WHERE goal LIKE ? OR answer LIKE ? ORDER BY id DESC LIMIT ?",
            (like, like, limit),
        ).fetchall()
        return [self._row(r) for r in rows]

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0])

    def close(self) -> None:
        self._conn.close()
