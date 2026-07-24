"""Minimal LangGraph scaffold.

Day 22 wires a single-node graph end to end so the plumbing (state schema,
entry point, compilation, invocation) is proven. Days 23-26 add the
Planner, worker, and Critic nodes and the retry loop.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.state import AgentState


def _start_node(state: AgentState) -> AgentState:
    """Placeholder node: records that the graph ran."""
    scratchpad = list(state.get("scratchpad", []))
    scratchpad.append({"node": "start", "content": f"received goal: {state.get('goal', '')}"})
    return {"scratchpad": scratchpad}


def build_graph():
    """Compile and return the (currently single-node) agent graph."""
    graph = StateGraph(AgentState)
    graph.add_node("start", _start_node)
    graph.set_entry_point("start")
    graph.add_edge("start", END)
    return graph.compile()
