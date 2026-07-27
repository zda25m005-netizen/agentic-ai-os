"""RAG search tool: query the agent's own ingested documents.

Bridges the RAG engine (Weeks 1-3) into the agent's toolset. A "research"
step can now search the internal knowledge base in Qdrant, not just the
web — grounded, source-tagged answers over your enterprise documents.
"""
from __future__ import annotations

from app.core import llm
from app.rag import retriever, vectorstore
from app.tools.registry import tool


@tool(
    name="rag_search",
    description="Search the internal document knowledge base for relevant passages.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to look up"},
            "top_k": {"type": "integer", "description": "Max passages (default 3)"},
        },
        "required": ["query"],
    },
)
async def rag_search(query: str, top_k: int = 3) -> str:
    """Tool handler: retrieve internal passages for the query."""
    if not llm.is_configured():
        return "error: embeddings not configured (set OPENAI_API_KEY)"
    client = vectorstore.get_client()
    hits = await retriever.retrieve(query, client, limit=top_k)
    if not hits:
        return "No relevant internal documents found."
    lines = []
    for i, h in enumerate(hits, start=1):
        source = h.payload.get("source", "unknown")
        text = (h.payload.get("text", "") or "")[:300]
        lines.append(f"[{i}] ({source}) {text}")
    return "\n\n".join(lines)
