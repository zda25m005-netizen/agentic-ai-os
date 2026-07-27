"""SQL query tool: read-only queries over a relational database.

Lets the agent answer questions over structured data by running SQL.
Safety first: only a single SELECT/WITH statement is allowed — writes,
DDL, and multi-statement inputs are rejected before execution, so the
agent can read data but never mutate it.

Uses SQLite (stdlib) so tests and CI need no DB server. Point SQL_DB_PATH
at a real database file to use it for real; swapping to Postgres is a
connection-factory change (see DESIGN.md).
"""
from __future__ import annotations

import re
import sqlite3

from app.core.config import get_settings
from app.tools.registry import tool

MAX_ROWS = 50

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|truncate|attach|"
    r"detach|pragma|vacuum|reindex)\b",
    re.IGNORECASE,
)


def is_read_only(sql: str) -> bool:
    """True only for a single SELECT/WITH statement with no write keywords."""
    stripped = sql.strip().rstrip(";").strip()
    if not stripped:
        return False
    if ";" in stripped:  # reject stacked statements
        return False
    if not stripped.lower().startswith(("select", "with")):
        return False
    return _FORBIDDEN.search(stripped) is None


def run_query(sql: str, conn: sqlite3.Connection, max_rows: int = MAX_ROWS) -> list[dict]:
    """Execute a read-only query and return rows as dicts."""
    cur = conn.execute(sql)
    columns = [d[0] for d in cur.description or []]
    rows = cur.fetchmany(max_rows)
    return [dict(zip(columns, row, strict=True)) for row in rows]


def format_rows(rows: list[dict]) -> str:
    """Render rows as a compact Markdown table."""
    if not rows:
        return "(0 rows)"
    columns = list(rows[0].keys())
    lines = ["| " + " | ".join(columns) + " |",
             "|" + "|".join("---" for _ in columns) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(row[c]) for c in columns) + " |")
    return "\n".join(lines)


def get_connection() -> sqlite3.Connection:
    """Open the configured SQLite database (in-memory if unset)."""
    path = getattr(get_settings(), "sql_db_path", "") or ":memory:"
    return sqlite3.connect(path)


@tool(
    name="sql_query",
    description="Run a read-only SQL SELECT query against the database.",
    parameters={
        "type": "object",
        "properties": {
            "sql": {"type": "string", "description": "A single SELECT statement"},
        },
        "required": ["sql"],
    },
)
async def sql_query(sql: str) -> str:
    """Tool handler: validate, execute, and format a read-only query."""
    if not is_read_only(sql):
        return "error: only a single read-only SELECT/WITH query is allowed"
    conn = get_connection()
    try:
        rows = run_query(sql, conn)
    except sqlite3.Error as exc:
        return f"error: {exc}"
    finally:
        conn.close()
    return format_rows(rows)
