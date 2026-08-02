"""Graph search tool: query the knowledge graph for related facts.

Complements `rag_search` (prose passages) with structured relationships. The
agent can call this when a goal is relational ("how is X connected to Y?").
Returns serialized subgraph triples around the query's entities.
"""
from __future__ import annotations

from app.core import llm
from app.graph.retrieval import get_graph_context
from app.tools.registry import tool


@tool(
    name="graph_search",
    description=(
        "Query the knowledge graph for facts and relationships between entities "
        "relevant to a question. Best for relational or multi-hop questions."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to look up"},
            "hops": {"type": "integer", "description": "Traversal depth 1-3 (default 2)"},
        },
        "required": ["query"],
    },
)
async def graph_search(query: str, hops: int = 2) -> str:
    """Tool handler: return graph facts around the query's entities."""
    if not llm.is_configured():
        return "error: LLM not configured (set OPENAI_API_KEY)"
    try:
        ctx = await get_graph_context(query, hops=hops)
    except Exception as exc:  # noqa: BLE001
        return f"error: knowledge graph unavailable ({exc})"
    if not ctx.triples:
        return "No related facts found in the knowledge graph."
    return ctx.text
