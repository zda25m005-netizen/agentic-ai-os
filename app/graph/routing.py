"""Route relational goals toward the knowledge graph.

A cheap, deterministic heuristic that spots goals phrased as relationships or
multi-hop questions, so the planner can nudge the executor to reach for
`graph_search` (structured facts) rather than only prose retrieval.
"""
from __future__ import annotations

# Phrasings that signal a relationship / traversal question.
RELATIONAL_MARKERS = (
    "related", "relationship", "connection", "connected", "linked", "link between",
    "between", "how does", "how is", "how are", "depend", "associated",
    "tied to", "report to", "reports to", "who owns", "part of",
)

GRAPH_HINT = (
    "This goal looks relational. Prefer the graph_search tool to find the "
    "entities involved and how they connect in the knowledge graph, then "
    "combine with document search if needed."
)


def is_relational_goal(goal: str) -> bool:
    """True if the goal reads like a relationship/multi-hop question."""
    g = (goal or "").lower()
    return any(marker in g for marker in RELATIONAL_MARKERS)
