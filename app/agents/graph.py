"""The full multi-agent graph: Planner -> Executor -> Critic -> (loop | finalize).

    planner --> executor --> critic --approve & more steps--> executor
                                 |  --retry--> executor (same step)
                                 |  --approve & done--> finalize --> END

The Critic's conditional edge is what makes this agentic: after every step
it decides whether to keep going, redo the step, or finish. `is_done`
(cursor past the last step) routes to the finalizer; otherwise the graph
re-enters the Executor — either on the next step or a rolled-back retry.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.critic import critic_node
from app.agents.executor import executor_node, is_done
from app.agents.planner import planner_node
from app.agents.state import AgentState, new_state


def finalize_node(state: AgentState) -> AgentState:
    """Synthesize the final answer from the collected step results."""
    results = state.get("results", [])
    answer = "\n\n".join(results)
    scratchpad = list(state.get("scratchpad", []))
    scratchpad.append({"node": "finalize", "content": "synthesized final answer"})
    return {"answer": answer, "scratchpad": scratchpad}


def _route_after_critic(state: AgentState) -> str:
    """After review: finish if the plan is complete, else run another step."""
    return "finalize" if is_done(state) else "executor"


def build_graph():
    """Compile the full Planner -> Executor -> Critic -> Finalize graph."""
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("critic", critic_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "critic")
    graph.add_conditional_edges(
        "critic",
        _route_after_critic,
        {"executor": "executor", "finalize": "finalize"},
    )
    graph.add_edge("finalize", END)
    return graph.compile()


async def run_agent(goal: str, recursion_limit: int = 50) -> AgentState:
    """Run the full agent graph on a goal and return the final state."""
    graph = build_graph()
    return await graph.ainvoke(
        new_state(goal), config={"recursion_limit": recursion_limit}
    )
