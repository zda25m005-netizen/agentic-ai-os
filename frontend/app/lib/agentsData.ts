// ---------------------------------------------------------------------------
// Agent catalog — the real role-specialized agents in the mission runtime
// (Planner / Executor / Critic / Researcher / Analyst). Descriptions, roles and
// loop positions are real. `tools` is the curated capability association (which
// tools each role invokes) — a display mapping, not a backend permission table,
// and clearly labelled as such. Per-agent execution telemetry (success / latency
// / cost) is NOT exposed over HTTP, so it is not shown here — aggregate runtime
// metrics live on Observability. Nothing is fabricated.
// ---------------------------------------------------------------------------

export type AgentStatus = "active" | "idle" | "degraded" | "error" | "disabled";
export type RoleGroup = "Planning" | "Execution" | "Evaluation" | "Research" | "Analysis";

export interface AgentView {
  id: string;
  name: string;
  role: RoleGroup;
  status: AgentStatus;
  loopStage: string;      // position in the Planner→Executor→Critic loop
  description: string;
  responsibilities: string[];
  tools: string[];        // tool ids (link to /tools) — curated association
}

export const AGENTS: AgentView[] = [
  { id: "planner", name: "Planner", role: "Planning", status: "active", loopStage: "Plan",
    description: "Decomposes a mission into subgoals and dependencies before execution.",
    responsibilities: ["Task decomposition", "Dependency resolution", "Execution planning"],
    tools: ["subagent"] },
  { id: "executor", name: "Executor", role: "Execution", status: "active", loopStage: "Execute",
    description: "Runs each ready task through the tool-use loop.",
    responsibilities: ["Tool-use loop", "Step execution", "Result capture"],
    tools: ["web_search", "python_exec", "calculator", "data_analysis", "file_ops", "http_tool", "sql_tool", "wikipedia"] },
  { id: "critic", name: "Critic / Judge", role: "Evaluation", status: "active", loopStage: "Evaluate",
    description: "Scores output quality and, on rejection, triggers a bounded replan.",
    responsibilities: ["Output scoring", "Acceptance / rejection", "Bounded replanning"],
    tools: [] },
  { id: "researcher", name: "Researcher", role: "Research", status: "active", loopStage: "Execute",
    description: "Gathers facts and sources for a subtask, grounding findings in retrieved evidence.",
    responsibilities: ["Source gathering", "Evidence grounding", "Citation capture"],
    tools: ["web_search", "rag_search", "wikipedia", "graph_search"] },
  { id: "analyst", name: "Analyst", role: "Analysis", status: "active", loopStage: "Execute",
    description: "Reasons over tradeoffs and produces structured analysis from gathered evidence.",
    responsibilities: ["Tradeoff analysis", "Structured synthesis", "Recommendation"],
    tools: ["python_exec", "data_analysis", "calculator"] },
];

export const ROLE_GROUPS: RoleGroup[] = ["Planning", "Execution", "Evaluation", "Research", "Analysis"];

// The agent loop (real): Planner → Executor → Critic → (replan) → Finalize.
export const LOOP = ["Planner", "Executor", "Critic", "Finalize"];

export const STATUS_LABEL: Record<AgentStatus, string> = {
  active: "Active", idle: "Idle", degraded: "Degraded", error: "Error", disabled: "Disabled",
};
