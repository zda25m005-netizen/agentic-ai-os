"""Ingest extracted entities/relations into Neo4j.

Every write is a `MERGE`, so ingest is idempotent: re-running over the same
corpus updates in place instead of duplicating nodes/edges. Each entity is
linked back to its source chunk via `MENTIONED_IN`, so a graph answer can still
cite where it came from.

The Cypher-building step (`build_ops`) is pure and unit-tested; execution
(`run_ops`) is a thin loop over a session, so tests can record the exact
statements without a live database.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.graph.client import graph_session
from app.graph.extract import extract_graph
from app.graph.schema import GraphExtraction

# Idempotent writes. Entity name is the identity key; type is (re)set each time.
MERGE_ENTITY = "MERGE (e:Entity {name: $name}) SET e.type = $type"
MERGE_CHUNK = "MERGE (c:Chunk {id: $chunk_id})"
LINK_MENTION = (
    "MATCH (e:Entity {name: $name}) MATCH (c:Chunk {id: $chunk_id}) "
    "MERGE (e)-[:MENTIONED_IN]->(c)"
)
MERGE_RELATION = (
    "MATCH (s:Entity {name: $subject}) MATCH (o:Entity {name: $object}) "
    "MERGE (s)-[:RELATION {predicate: $predicate}]->(o)"
)

# Schema/perf setup — run once before ingest. Idempotent (IF NOT EXISTS).
# The name index makes entity lookups (seed matching in retrieval) fast.
SCHEMA_STATEMENTS = [
    "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
    "CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS "
    "FOR (c:Chunk) REQUIRE c.id IS UNIQUE",
]

ExtractFn = Callable[[str], Awaitable[GraphExtraction]]


def ensure_graph_schema(driver=None) -> int:
    """Create the entity-name index and chunk-id constraint (idempotent)."""
    with graph_session(driver) as session:
        for stmt in SCHEMA_STATEMENTS:
            session.run(stmt, {})
    return len(SCHEMA_STATEMENTS)


@dataclass
class IngestStats:
    """Totals across an ingest run."""

    documents: int = 0
    entities: int = 0
    relations: int = 0
    operations: int = 0


def build_ops(
    extraction: GraphExtraction, chunk_id: str | None = None
) -> list[tuple[str, dict]]:
    """Turn an extraction into an ordered list of (cypher, params) writes."""
    ops: list[tuple[str, dict]] = []
    if chunk_id is not None:
        ops.append((MERGE_CHUNK, {"chunk_id": chunk_id}))
    for e in extraction.entities:
        ops.append((MERGE_ENTITY, {"name": e.name, "type": e.type}))
        if chunk_id is not None:
            ops.append((LINK_MENTION, {"name": e.name, "chunk_id": chunk_id}))
    for r in extraction.relations:
        ops.append(
            (
                MERGE_RELATION,
                {"subject": r.subject, "object": r.object, "predicate": r.predicate},
            )
        )
    return ops


def run_ops(ops: list[tuple[str, dict]], driver=None) -> int:
    """Execute a batch of (cypher, params) writes in one session."""
    with graph_session(driver) as session:
        for cypher, params in ops:
            session.run(cypher, params)
    return len(ops)


def ingest_extraction(
    extraction: GraphExtraction, chunk_id: str | None = None, driver=None
) -> int:
    """MERGE one chunk's extraction into the graph. Returns ops executed."""
    return run_ops(build_ops(extraction, chunk_id), driver)


async def ingest_documents(
    docs: list[dict], extract_fn: ExtractFn | None = None, driver=None
) -> IngestStats:
    """Extract and ingest a corpus of ``{"source", "text"}`` documents."""
    extract_fn = extract_fn or extract_graph
    stats = IngestStats()
    for doc in docs:
        chunk_id = doc.get("source") or doc.get("id") or "unknown"
        extraction = await extract_fn(doc.get("text", ""))
        stats.operations += ingest_extraction(extraction, chunk_id, driver)
        stats.entities += len(extraction.entities)
        stats.relations += len(extraction.relations)
        stats.documents += 1
    return stats
