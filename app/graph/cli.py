"""CLI to build the knowledge graph from a JSON corpus.

Usage:
    python -m app.graph.cli --corpus eval/datasets/corpus.json

Reads ``[{"source", "text"}, ...]``, extracts entities/relations with the LLM,
and MERGEs them into Neo4j. Requires a running Neo4j (docker compose up neo4j)
and a configured LLM. Ingest is idempotent, so re-running is safe.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.graph.ingest import ensure_graph_schema, ingest_documents

DEFAULT_CORPUS = "eval/datasets/corpus.json"


async def _run(corpus_path: str) -> None:
    docs = json.loads(Path(corpus_path).read_text())
    ensure_graph_schema()
    print(f"Ingesting {len(docs)} document(s) into the graph...")
    stats = await ingest_documents(docs)
    print(
        f"Done: {stats.documents} docs, {stats.entities} entities, "
        f"{stats.relations} relations, {stats.operations} graph writes."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Neo4j knowledge graph.")
    parser.add_argument("--corpus", default=DEFAULT_CORPUS, help="Path to corpus JSON.")
    args = parser.parse_args()
    asyncio.run(_run(args.corpus))


if __name__ == "__main__":
    main()
