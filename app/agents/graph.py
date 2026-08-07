"""The full multi-agent graph: Planner -> Executor -> Critic -> (loop | finalize).

    planner --> executor --> critic --approve & more steps--> executor
                                 |  --retry--> executor (same step)
                                 |  --approve & done--> finalize --> END

The Critic's conditional edge is what makes this agentic: after every step
it decides whether to keep going, redo the step, or finish. The finalizer
synthesizes the answer and persists the run to long-term memory (if set).
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.critic import critic_node
from app.agents.executor import executor_node, is_done
from app.agents.planner import planner_node
from app.agents.state import AgentState, new_state
from app.memory.manager import get_memory
from app.obs import metrics


def _counted(node_name: str, fn):
    """Wrap a graph node so each execution increments its Prometheus counter."""

    async def wrapper(state: AgentState) -> AgentState:
        metrics.inc_agent_node(node_name)
        return await fn(state)

    return wrapper


async def finalize_node(state: AgentState) -> AgentState:
    """Synthesize the final answer and persist the run to memory (if set)."""
    results = state.get("results", [])
    answer = "\n\n".join(results)
    scratchpad = list(state.get("scratchpad", []))
    scratchpad.append({"node": "finalize", "content": "synthesized final answer"})

    memory = get_memory()
    if memory is not None:
        await memory.remember(state.get("goal", ""), answer)
        scratchpad.append({"node": "finalize", "content": "saved run to memory"})

    return {"answer": answer, "scratchpad": scratchpad}


def _route_after_critic(state: AgentState) -> str:
    """After review: finish if the plan is complete, else run another step."""
    return "finalize" if is_done(state) else "executor"


def build_graph():
    """Compile the full Planner -> Executor -> Critic -> Finalize graph."""
    graph = StateGraph(AgentState)
    graph.add_node("planner", _counted("planner", planner_node))
    graph.add_node("executor", _counted("executor", executor_node))
    graph.add_node("critic", _counted("critic", critic_node))
    graph.add_node("finalize", _counted("finalize", finalize_node))

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
