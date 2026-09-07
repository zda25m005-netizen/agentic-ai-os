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
from app.core import llm
from app.memory.manager import get_memory
from app.memory.orchestrator import get_orchestrator
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

    goal = state.get("goal", "")
    orch = get_orchestrator()
    if orch is not None:
        # Mem0-style lifecycle: log the run episodically, then extract + resolve
        # durable candidate memories from goal + answer (config D).
        from app.core.config import get_settings
        from app.memory.lifecycle import (
            extract_candidates,
            extract_candidates_llm,
            resolve_and_ingest,
        )

        orch.remember(
            f"Goal: {goal} -> {answer}",
            memory_type="episodic",
            source="agent",
            confidence=0.6,
            mission_id=state.get("mission_id"),
        )
        settings = get_settings()
        text = f"{goal}\n{answer}"
        if settings.memory_policy_mode == "llm" and llm.is_configured():
            candidates = await extract_candidates_llm(text, llm.chat, source="agent")
        else:
            candidates = extract_candidates(text, source="agent")
        # Config F: use the learned RL policy for the resolve decision when enabled;
        # get_policy degrades to the deterministic policy if weights are missing.
        from app.memory.policy import get_policy

        policy = get_policy(
            settings.memory_policy_mode,
            weights_path=settings.memory_policy_weights,
            backend=settings.memory_policy_backend,
            llm_model=settings.memory_llm_model,
            lora_adapter=settings.memory_lora_adapter,
        )
        result = resolve_and_ingest(
            orch, candidates, mission_id=state.get("mission_id"), policy=policy
        )
        ops = result["ops"]
        summary = f"memory lifecycle: {ops['ADD']} add, {ops['UPDATE']} update, {ops['NOOP']} noop"
        scratchpad.append({"node": "finalize", "content": summary})

        # Config E: also project the durable facts into the owner-scoped graph memory.
        # No-op unless MEMORY_GRAPH_ENABLED and a live Neo4j answers — the agent path
        # is otherwise unchanged, so tests without a graph DB are unaffected.
        if get_settings().memory_graph_enabled:
            from app.memory.graph_memory import GraphMemory

            gm = GraphMemory(owner=orch.owner)
            g = await gm.ingest_text(text, chat_fn=llm.chat if llm.is_configured() else None)
            if g["ops"]:
                scratchpad.append(
                    {
                        "node": "finalize",
                        "content": f"graph memory: {g['entities']} entities, "
                        f"{g['relations']} relations",
                    }
                )
    else:
        memory = get_memory()  # legacy fallback (preserves existing behavior/tests)
        if memory is not None:
            await memory.remember(goal, answer)
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
    return await graph.ainvoke(new_state(goal), config={"recursion_limit": recursion_limit})
