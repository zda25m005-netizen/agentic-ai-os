"""Neo4j graph client.

Thin, typed wrapper over the official ``neo4j`` driver, mirroring the Qdrant
vectorstore wrapper so the rest of the app stays decoupled from the SDK.

The driver maintains its own internal connection pool, so we cache a single
driver per process and reuse it. Tests monkeypatch ``GraphDatabase.driver``,
so no live Neo4j is required in CI.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from neo4j import Driver, GraphDatabase, Session

from app.core.config import get_settings

# Process-wide cached driver (owns the connection pool).
_driver: Driver | None = None


def get_graph_driver(
    uri: str | None = None,
    user: str | None = None,
    password: str | None = None,
) -> Driver:
    """Return a Neo4j driver.

    With no arguments this returns a cached, pooled driver built from config.
    Passing an explicit ``uri`` returns a fresh (uncached) driver — used by
    tests and by callers that need to target a specific instance.
    """
    global _driver
    if uri is None and _driver is not None:
        return _driver

    s = get_settings()
    driver = GraphDatabase.driver(
        uri or s.neo4j_uri,
        auth=(user or s.neo4j_user, password or s.neo4j_password),
    )
    if uri is None:
        _driver = driver
    return driver


@contextmanager
def graph_session(
    driver: Driver | None = None, database: str | None = None
) -> Iterator[Session]:
    """Yield a session from the driver and always close it."""
    d = driver or get_graph_driver()
    session = d.session(database=database) if database else d.session()
    try:
        yield session
    finally:
        session.close()


def run_query(
    cypher: str,
    params: dict[str, Any] | None = None,
    driver: Driver | None = None,
) -> list[dict]:
    """Run a Cypher statement and return rows as plain dicts."""
    with graph_session(driver) as session:
        result = session.run(cypher, params or {})
        return [record.data() for record in result]


def verify_connectivity(driver: Driver | None = None) -> bool:
    """Return True if the graph DB answers a trivial query."""
    try:
        rows = run_query("RETURN 1 AS ok", driver=driver)
        return bool(rows) and rows[0].get("ok") == 1
    except Exception:
        return False


def close_driver() -> None:
    """Close and clear the cached driver (call on shutdown / in tests)."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
