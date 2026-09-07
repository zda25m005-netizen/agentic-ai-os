"""Graph memory (Mem0g-style) — an entity/relationship layer over long-term memory.

Reuses the existing knowledge-graph stack (``app/graph``): the same LLM extraction
(``extract_graph``) and the same Neo4j client (``run_query`` / ``graph_session`` /
``verify_connectivity``). Memory facts are projected into their own **owner-scoped**
node/edge namespace so they never collide with the document RAG graph and never leak
across owners.

Design guarantees:
- **Optional + graceful.** Enabled by ``MEMORY_GRAPH_ENABLED`` and only active when a
  live Neo4j answers ``verify_connectivity``. When unavailable, every method is a safe
  no-op (ingest returns 0, retrieval returns an empty context) — so the agent, the API,
  and the entire test suite work unchanged without a graph database.
- **Owner isolation.** Every node and relationship carries ``owner``; every MATCH/MERGE
  filters on ``$owner``. One owner's memory graph is never traversed for another.
- **Advisory only.** Retrieved triples are returned as clearly-labelled context; like the
  rest of the memory engine, they personalize and never override the current request.
- **Separate namespace.** Uses ``:MemEntity`` / ``:MEM_RELATION`` (not the doc graph's
  ``:Entity`` / ``:RELATION``), so graph memory and document-KG ingest stay decoupled.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.graph.client import graph_session, run_query, verify_connectivity
from app.graph.extract import extract_entities, extract_graph
from app.graph.normalize import normalize_name
from app.graph.retrieval import serialize_triples
from app.graph.schema import GraphExtraction

ChatFn = Callable[[list[dict]], Awaitable[str]]

_MAX_HOPS = 3

# Owner-scoped, idempotent writes (a distinct namespace from the document KG).
_MERGE_ENTITY = "MERGE (e:MemEntity {owner: $owner, name: $name}) SET e.type = $type"
_MERGE_RELATION = (
    "MATCH (s:MemEntity {owner: $owner, name: $subject}) "
    "MATCH (o:MemEntity {owner: $owner, name: $object}) "
    "MERGE (s)-[:MEM_RELATION {owner: $owner, predicate: $predicate}]->(o)"
)
_SCHEMA = [
    "CREATE INDEX mem_entity_owner_name IF NOT EXISTS " "FOR (e:MemEntity) ON (e.owner, e.name)",
]


def _neighborhood_query(hops: int) -> str:
    """Owner-scoped k-hop neighborhood around seed entities (see graph.retrieval)."""
    hops = max(1, min(int(hops), _MAX_HOPS))
    return (
        "MATCH (e:MemEntity) WHERE e.owner = $owner AND toLower(e.name) IN $names "
        f"MATCH (e)-[rels:MEM_RELATION*1..{hops}]-(:MemEntity {{owner: $owner}}) "
        "UNWIND rels AS rel "
        "RETURN DISTINCT startNode(rel).name AS subject, "
        "rel.predicate AS predicate, endNode(rel).name AS object"
    )


class GraphMemory:
    """Owner-scoped entity/relationship memory backed by Neo4j (optional)."""

    _HEADER = "Related facts from memory graph (advisory — the current request takes precedence):"

    def __init__(self, owner: str = "me", driver=None):
        self.owner = owner
        self.driver = driver
        self._available: bool | None = None

    # --- availability --------------------------------------------------------
    def available(self) -> bool:
        """True only if a live Neo4j answers. Cached; never raises."""
        if self._available is None:
            try:
                self._available = verify_connectivity(self.driver)
            except Exception:
                self._available = False
        return self._available

    def ensure_schema(self) -> int:
        if not self.available():
            return 0
        try:
            with graph_session(self.driver) as session:
                for stmt in _SCHEMA:
                    session.run(stmt, {})
            return len(_SCHEMA)
        except Exception:
            return 0

    # --- write ---------------------------------------------------------------
    def _build_ops(self, extraction: GraphExtraction) -> list[tuple[str, dict]]:
        ops: list[tuple[str, dict]] = []
        for e in extraction.entities:
            ops.append((_MERGE_ENTITY, {"owner": self.owner, "name": e.name, "type": e.type}))
        for r in extraction.relations:
            ops.append(
                (
                    _MERGE_RELATION,
                    {
                        "owner": self.owner,
                        "subject": r.subject,
                        "object": r.object,
                        "predicate": r.predicate,
                    },
                )
            )
        return ops

    async def ingest_text(self, text: str, *, chat_fn: ChatFn | None = None) -> dict:
        """Extract entities/relations from ``text`` and MERGE them (owner-scoped).

        No-op (returns zeros) when the graph is unavailable, so callers need no guard.
        """
        if not text or not self.available():
            return {"entities": 0, "relations": 0, "ops": 0}
        try:
            extraction = await extract_graph(text, chat_fn)
            ops = self._build_ops(extraction)
            if ops:
                with graph_session(self.driver) as session:
                    for cypher, params in ops:
                        session.run(cypher, params)
            return {
                "entities": len(extraction.entities),
                "relations": len(extraction.relations),
                "ops": len(ops),
            }
        except Exception:
            return {"entities": 0, "relations": 0, "ops": 0}

    # --- read ----------------------------------------------------------------
    async def related(
        self,
        query: str,
        *,
        hops: int = 2,
        chat_fn: ChatFn | None = None,
        extract_fn=None,
    ) -> dict:
        """Return the owner's subgraph relevant to ``query`` as triples + text.

        Empty result when unavailable. The returned ``context`` is advisory only.
        """
        empty = {"triples": [], "text": "", "context": ""}
        if not query or not self.available():
            return empty
        try:
            # Default extractor is the shared LLM one; a custom extract_fn (e.g. in
            # tests) is called with just the query, mirroring app.graph.retrieval.
            if extract_fn is None:
                entities = await extract_entities(query, chat_fn)
            else:
                entities = await extract_fn(query)
            names = [normalize_name(e.name).casefold() for e in entities if e.name]
            if not names:
                return empty
            params = {"owner": self.owner, "names": names}
            rows = run_query(_neighborhood_query(hops), params, self.driver)
            triples = [
                (r["subject"], r["predicate"], r["object"])
                for r in rows
                if r.get("subject") and r.get("object")
            ]
            if not triples:
                return empty
            text = serialize_triples(triples)
            return {"triples": triples, "text": text, "context": self._HEADER + "\n" + text}
        except Exception:
            return empty
