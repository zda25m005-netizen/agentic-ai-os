"""Graph retrieval: from a query to a relevant subgraph, as LLM context.

Pipeline: extract the entities named in the query → find those nodes in Neo4j →
pull their k-hop neighborhood of `RELATION` edges → serialize the resulting
triples into compact text the LLM can read alongside RAG passages.

The Cypher builder is pure (unit-tested), and `get_graph_context` takes an
injectable `extract_fn` and `driver`, so the whole path runs in CI with fakes.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from app.graph.client import run_query
from app.graph.extract import extract_entities
from app.graph.schema import Entity

# Callable that maps query text -> entities (defaults to the LLM extractor).
ExtractEntitiesFn = Callable[[str], Awaitable[list[Entity]]]

MAX_HOPS = 3


@dataclass
class GraphContext:
    """Retrieved subgraph as triples plus a serialized text block."""

    triples: list[tuple[str, str, str]] = field(default_factory=list)
    text: str = ""


def neighborhood_query(hops: int) -> str:
    """Cypher for the k-hop RELATION neighborhood around seed entities.

    `hops` is clamped to [1, MAX_HOPS] and injected as a literal (Cypher can't
    parameterize a variable-length bound); it's an int we control, so it's safe.
    Seed match is case-insensitive against `$names`.
    """
    hops = max(1, min(int(hops), MAX_HOPS))
    return (
        "MATCH (e:Entity) WHERE toLower(e.name) IN $names "
        f"MATCH (e)-[rels:RELATION*1..{hops}]-(:Entity) "
        "UNWIND rels AS rel "
        "RETURN DISTINCT startNode(rel).name AS subject, "
        "rel.predicate AS predicate, endNode(rel).name AS object"
    )


def serialize_triples(triples: list[tuple[str, str, str]]) -> str:
    """Render triples as compact, deduped lines for the prompt."""
    seen: set[tuple[str, str, str]] = set()
    lines: list[str] = []
    for s, p, o in triples:
        key = (s.casefold(), p.casefold(), o.casefold())
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"{s} —[{p}]→ {o}")
    return "\n".join(lines)


async def get_graph_context(
    query: str,
    driver=None,
    hops: int = 2,
    extract_fn: ExtractEntitiesFn | None = None,
) -> GraphContext:
    """Return the subgraph relevant to `query` as triples + serialized text."""
    extract_fn = extract_fn or extract_entities
    entities = await extract_fn(query)
    names = [e.name.casefold() for e in entities]
    if not names:
        return GraphContext()

    rows = run_query(neighborhood_query(hops), {"names": names}, driver)
    triples = [
        (r["subject"], r["predicate"], r["object"])
        for r in rows
        if r.get("subject") and r.get("object")
    ]
    return GraphContext(triples=triples, text=serialize_triples(triples))
