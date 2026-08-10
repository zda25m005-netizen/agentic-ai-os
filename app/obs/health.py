"""Readiness checks for the app's backing services.

Liveness (`/health`) says "the process is up." Readiness (`/readyz`) says "the
dependencies I need are reachable" — Qdrant (vectors), Neo4j (graph), Postgres
(memory). Each check is isolated and swallows errors, returning "up"/"down", so
one downed dependency degrades the report instead of raising.
"""
from __future__ import annotations


async def check_qdrant() -> str:
    try:
        from app.rag import vectorstore

        vectorstore.get_client().get_collections()
        return "up"
    except Exception:
        return "down"


async def check_neo4j() -> str:
    try:
        from app.graph.client import verify_connectivity

        return "up" if verify_connectivity() else "down"
    except Exception:
        return "down"


async def check_postgres() -> str:
    try:
        from app.db.session import database_healthy

        return "up" if await database_healthy() else "down"
    except Exception:
        return "down"


async def check_all() -> dict:
    """Return per-dependency status plus an overall ok/degraded verdict."""
    deps = {
        "qdrant": await check_qdrant(),
        "neo4j": await check_neo4j(),
        "postgres": await check_postgres(),
    }
    status = "ok" if all(v == "up" for v in deps.values()) else "degraded"
    return {"status": status, "deps": deps}
