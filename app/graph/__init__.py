"""Knowledge-graph layer (Neo4j): client, extraction, ingestion, retrieval."""

from app.graph.client import get_graph_driver, graph_session, run_query
from app.graph.extract import extract_graph
from app.graph.ingest import ensure_graph_schema, ingest_documents, ingest_extraction
from app.graph.retrieval import GraphContext, get_graph_context
from app.graph.schema import Entity, GraphExtraction, Relation

__all__ = [
    "get_graph_driver",
    "graph_session",
    "run_query",
    "extract_graph",
    "ingest_documents",
    "ingest_extraction",
    "ensure_graph_schema",
    "get_graph_context",
    "GraphContext",
    "Entity",
    "Relation",
    "GraphExtraction",
]
