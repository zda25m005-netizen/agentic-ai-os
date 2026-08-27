// Deterministic demo scenario for the Mission Workspace — no backend needed.
// Clearly labeled DEMO in the UI; not real production execution.

export type NodeState = "idle" | "queued" | "running" | "done" | "failed" | "retry";

export interface GraphNode {
  id: string;
  label: string;
  sub?: string;
  x: number;
  y: number;
}

export interface GraphEdge {
  from: string;
  to: string;
}

export interface TraceEvent {
  t: string;        // timestamp label
  comp: string;     // component
  ev: string;       // event type
  tokens: number;
  cost: number;
  status: "ok" | "fail" | "info";
}

export interface LiveState {
  agent: string;
  step: string;
  progress: string;
  tool: string;
  memoryHits: number;
  docs: number;
  tokens: number;
  cost: number;
  latency: number;
}

export interface DemoStep {
  states: Record<string, NodeState>;   // merged cumulatively
  activeEdge?: [string, string];        // edge to animate this step
  trace: TraceEvent;
  live: Partial<LiveState>;
}

export const NODES: GraphNode[] = [
  { id: "goal", label: "GOAL", x: 450, y: 34 },
  { id: "planner", label: "PLANNER", x: 450, y: 120 },
  { id: "research", label: "RESEARCH", sub: "web_search", x: 230, y: 230 },
  { id: "rag", label: "RAG", sub: "hybrid + rerank", x: 450, y: 230 },
  { id: "memory", label: "MEMORY", sub: "recall", x: 670, y: 230 },
  { id: "executor", label: "EXECUTOR", x: 450, y: 340 },
  { id: "critic", label: "CRITIC", x: 450, y: 430 },
  { id: "result", label: "RESULT", x: 450, y: 508 },
];

export const EDGES: GraphEdge[] = [
  { from: "goal", to: "planner" },
  { from: "planner", to: "research" },
  { from: "planner", to: "rag" },
  { from: "planner", to: "memory" },
  { from: "research", to: "executor" },
  { from: "rag", to: "executor" },
  { from: "memory", to: "executor" },
  { from: "executor", to: "critic" },
  { from: "critic", to: "executor" }, // retry (backward)
  { from: "critic", to: "result" },
];

// The scripted run: "Compare NVIDIA, AMD and Intel AI strategy."
export const STEPS: DemoStep[] = [
  { states: { goal: "running" }, trace: { t: "00:00.000", comp: "mission", ev: "MISSION_STARTED", tokens: 0, cost: 0, status: "info" }, live: { agent: "—", step: "Interpreting goal", progress: "0 / 6", tool: "—", tokens: 0, cost: 0, latency: 0.0 } },
  { states: { goal: "done", planner: "running" }, activeEdge: ["goal", "planner"], trace: { t: "00:00.412", comp: "planner", ev: "PLANNER_STARTED", tokens: 180, cost: 0.0004, status: "info" }, live: { agent: "Planner", step: "Decomposing into subgoals", progress: "0 / 6", tokens: 180, cost: 0.0004, latency: 0.41 } },
  { states: { planner: "done" }, trace: { t: "00:01.230", comp: "planner", ev: "PLAN_CREATED (6 tasks)", tokens: 640, cost: 0.0012, status: "ok" }, live: { step: "Plan created", progress: "0 / 6", tokens: 640, cost: 0.0012, latency: 1.23 } },
  { states: { research: "running" }, activeEdge: ["planner", "research"], trace: { t: "00:01.540", comp: "research", ev: "TOOL_CALL → web_search", tokens: 720, cost: 0.0016, status: "info" }, live: { agent: "Research Agent", step: "Find recent AI GPU market data", progress: "1 / 6", tool: "Web Search", docs: 0, tokens: 720, cost: 0.0016, latency: 1.54 } },
  { states: { research: "done", rag: "running" }, activeEdge: ["planner", "rag"], trace: { t: "00:02.480", comp: "rag", ev: "RETRIEVAL_STARTED", tokens: 1120, cost: 0.0024, status: "info" }, live: { agent: "RAG Agent", step: "Hybrid retrieval + rerank", progress: "2 / 6", tool: "RAG", docs: 18, tokens: 1120, cost: 0.0024, latency: 2.48 } },
  { states: { rag: "done", memory: "running" }, activeEdge: ["planner", "memory"], trace: { t: "00:03.010", comp: "memory", ev: "MEMORY_RETRIEVAL", tokens: 1240, cost: 0.0027, status: "ok" }, live: { agent: "Memory", step: "Recall prior findings", progress: "3 / 6", tool: "Memory", memoryHits: 12, tokens: 1240, cost: 0.0027, latency: 3.01 } },
  { states: { memory: "done", executor: "running" }, activeEdge: ["rag", "executor"], trace: { t: "00:03.760", comp: "executor", ev: "EXECUTOR_STARTED", tokens: 1680, cost: 0.0038, status: "info" }, live: { agent: "Executor", step: "Synthesize comparison", progress: "4 / 6", tool: "—", tokens: 1680, cost: 0.0038, latency: 3.76 } },
  { states: { executor: "done", critic: "running" }, activeEdge: ["executor", "critic"], trace: { t: "00:05.120", comp: "critic", ev: "CRITIC_STARTED", tokens: 2010, cost: 0.0045, status: "info" }, live: { agent: "Critic", step: "Judging draft", progress: "5 / 6", tokens: 2010, cost: 0.0045, latency: 5.12 } },
  { states: { critic: "failed" }, trace: { t: "00:05.890", comp: "critic", ev: "CRITIC → RETRY (Intel evidence thin)", tokens: 2140, cost: 0.0048, status: "fail" }, live: { step: "Rejected: incomplete evidence", progress: "5 / 6", tokens: 2140, cost: 0.0048, latency: 5.89 } },
  { states: { critic: "idle", executor: "retry" }, activeEdge: ["critic", "executor"], trace: { t: "00:06.140", comp: "executor", ev: "RETRY_STARTED → alt source", tokens: 2260, cost: 0.0051, status: "info" }, live: { agent: "Executor", step: "Retry with alternate source", progress: "5 / 6", tool: "Web Search", tokens: 2260, cost: 0.0051, latency: 6.14 } },
  { states: { executor: "done", critic: "running" }, activeEdge: ["executor", "critic"], trace: { t: "00:07.430", comp: "critic", ev: "CRITIC_STARTED", tokens: 2680, cost: 0.0059, status: "info" }, live: { agent: "Critic", step: "Re-judging", progress: "6 / 6", tokens: 2680, cost: 0.0059, latency: 7.43 } },
  { states: { critic: "done" }, activeEdge: ["critic", "result"], trace: { t: "00:08.010", comp: "critic", ev: "CRITIC_PASSED (0.91)", tokens: 2740, cost: 0.0061, status: "ok" }, live: { step: "Accepted", progress: "6 / 6", tokens: 2740, cost: 0.0061, latency: 8.01 } },
  { states: { result: "done" }, trace: { t: "00:08.210", comp: "mission", ev: "MISSION_COMPLETED", tokens: 2740, cost: 0.0061, status: "ok" }, live: { agent: "—", step: "Done", progress: "6 / 6", tokens: 2740, cost: 0.0061, latency: 8.21 } },
];

export const FINAL_ANSWER =
  "NVIDIA leads on full-stack AI (CUDA + H100/H200 + networking); AMD competes on price/perf with MI300 and an open ROCm stack; Intel trails but bets on Gaudi accelerators and foundry. For training at scale, NVIDIA remains default; AMD is the strongest value challenger; Intel is a watch-list bet.";
