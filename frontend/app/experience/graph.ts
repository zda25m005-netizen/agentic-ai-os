// Data model for the interactive agent network (World 1, Chapter 4+).
// Node positions live in 3D (X,Y,Z depth). Kept as data so the architecture
// visualization can grow without editing JSX. Concepts map to the REAL system:
// agents (planner/executor/critic + specialists), tools, memory, system services, stores.

export type NodeKind = "agent" | "system" | "memory" | "tool" | "data";

export interface GNode {
  id: string;
  label: string;
  kind: NodeKind;
  pos: [number, number, number];
  desc: string;
  size?: number;
}

export type GEdge = [string, string];

export const KIND_COLOR: Record<NodeKind, string> = {
  agent: "#6EA8FF",
  system: "#C9D3E0",
  memory: "#8B7DF6",
  tool: "#4ADE80",
  data: "#F5C542",
};

// Key labelled nodes (agents get a little more presence).
export const NODES: GNode[] = [
  // agents (front, near center)
  { id: "planner", label: "Planner", kind: "agent", pos: [0, 1.2, 0], size: 1.35, desc: "Breaks a mission into executable steps." },
  { id: "researcher", label: "Researcher", kind: "agent", pos: [-3.4, 0.4, -2], size: 1.2, desc: "Gathers sources and grounds findings in evidence." },
  { id: "coder", label: "Coder", kind: "agent", pos: [3.4, 0.6, -2], size: 1.2, desc: "Writes, runs and fixes code." },
  { id: "analyst", label: "Analyst", kind: "agent", pos: [-2.2, -2.0, -3], size: 1.15, desc: "Turns messy data into a clear story." },
  { id: "critic", label: "Critic", kind: "agent", pos: [1.8, -1.8, -3.5], size: 1.15, desc: "Reviews results; approves or sends back for retry." },
  { id: "browser", label: "Browser Agent", kind: "agent", pos: [5.2, -0.6, -5], size: 1.0, desc: "Navigates the live web." },
  { id: "memory-agent", label: "Memory Agent", kind: "agent", pos: [-5.0, -0.8, -5], size: 1.0, desc: "Decides what to remember and recall." },
  { id: "data-agent", label: "Data Agent", kind: "agent", pos: [-1.0, 2.6, -6], size: 1.0, desc: "Loads and shapes structured data." },
  // system services
  { id: "mission-runtime", label: "Mission Runtime", kind: "system", pos: [0, 3.4, -8], desc: "Schedules and recovers long-running missions." },
  { id: "scheduler", label: "Scheduler", kind: "system", pos: [2.4, 2.4, -9], desc: "Runs tasks, some concurrently." },
  { id: "tool-registry", label: "Tool Registry", kind: "system", pos: [4.6, 1.6, -10], desc: "The set of tools agents may call." },
  { id: "policy", label: "Policy", kind: "system", pos: [3.2, -2.6, -10], desc: "Rules that gate risky actions." },
  { id: "approval", label: "Approval", kind: "system", pos: [1.2, -3.4, -11], desc: "Human-in-the-loop confirmation." },
  { id: "verification", label: "Verification", kind: "system", pos: [-1.6, -3.2, -11], desc: "Checks results before they finish." },
  { id: "artifact-store", label: "Artifact Store", kind: "system", pos: [-3.6, -2.4, -12], desc: "Where finished outputs live." },
  // memory
  { id: "working", label: "Working Memory", kind: "memory", pos: [-6.4, -2.4, -8], desc: "The current scratchpad." },
  { id: "episodic", label: "Episodic Memory", kind: "memory", pos: [-7.2, -1.0, -10], desc: "Past mission moments." },
  { id: "semantic", label: "Semantic Memory", kind: "memory", pos: [-6.6, 0.6, -12], desc: "Durable knowledge." },
  { id: "procedural", label: "Procedural Memory", kind: "memory", pos: [-5.4, 1.8, -13], desc: "Learned workflows." },
  // tools
  { id: "web", label: "Web Search", kind: "tool", pos: [-4.8, 1.6, -3.5], desc: "Search the open web." },
  { id: "python", label: "Python", kind: "tool", pos: [4.8, 1.8, -3.5], desc: "Execute code." },
  { id: "sql", label: "SQL", kind: "tool", pos: [5.6, 0.2, -4.5], desc: "Query databases." },
  { id: "files", label: "Files", kind: "tool", pos: [4.2, -1.4, -4.5], desc: "Read and write files." },
  { id: "rag", label: "RAG", kind: "tool", pos: [-5.6, 0.2, -4.5], desc: "Retrieve from documents." },
  { id: "graphrag", label: "GraphRAG", kind: "tool", pos: [-4.4, -1.4, -5], desc: "Retrieve over a knowledge graph." },
  { id: "http", label: "HTTP", kind: "tool", pos: [6.0, -1.8, -6], desc: "Call external APIs." },
  // data / knowledge (deep)
  { id: "qdrant", label: "Qdrant", kind: "data", pos: [-7.6, 1.2, -16], desc: "Vector store." },
  { id: "neo4j", label: "Neo4j", kind: "data", pos: [-6.0, 2.6, -17], desc: "Knowledge graph store." },
  { id: "postgres", label: "Postgres", kind: "data", pos: [-3.0, 3.2, -16], desc: "Relational store." },
  { id: "documents", label: "Documents", kind: "data", pos: [-8.4, -0.4, -15], desc: "Source corpus." },
  { id: "knowledge-graph", label: "Knowledge Graph", kind: "data", pos: [-5.0, 3.8, -18], desc: "Entities and relations." },
];

// Recenter the graph so its horizontal/vertical center sits at world origin (0,0).
// Node coordinates are shifted here (not via CSS/canvas translation) so the network
// renders centered in the viewport. Z depth is preserved untouched.
(() => {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const n of NODES) {
    if (n.pos[0] < minX) minX = n.pos[0];
    if (n.pos[0] > maxX) maxX = n.pos[0];
    if (n.pos[1] < minY) minY = n.pos[1];
    if (n.pos[1] > maxY) maxY = n.pos[1];
  }
  const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
  for (const n of NODES) { n.pos[0] -= cx; n.pos[1] -= cy; }
})();

// Central depth of the graph (Z bounding-box center). The camera aims here and the
// cursor interaction plane sits at this depth, so the whole network stays centered.
export const GRAPH_CENTER_Z: number = (() => {
  let minZ = Infinity, maxZ = -Infinity;
  for (const n of NODES) {
    if (n.pos[2] < minZ) minZ = n.pos[2];
    if (n.pos[2] > maxZ) maxZ = n.pos[2];
  }
  return (minZ + maxZ) / 2;
})();

export const EDGES: GEdge[] = [
  ["mission-runtime", "planner"], ["planner", "scheduler"], ["planner", "researcher"],
  ["planner", "coder"], ["planner", "analyst"], ["planner", "critic"], ["planner", "memory-agent"],
  ["researcher", "web"], ["researcher", "rag"], ["researcher", "browser"], ["browser", "web"],
  ["rag", "qdrant"], ["rag", "documents"], ["graphrag", "neo4j"], ["graphrag", "knowledge-graph"],
  ["researcher", "graphrag"], ["coder", "python"], ["coder", "files"], ["analyst", "sql"],
  ["analyst", "data-agent"], ["data-agent", "postgres"], ["data-agent", "sql"],
  ["memory-agent", "working"], ["memory-agent", "episodic"], ["memory-agent", "semantic"],
  ["memory-agent", "procedural"], ["episodic", "qdrant"], ["semantic", "qdrant"],
  ["critic", "verification"], ["verification", "policy"], ["policy", "approval"],
  ["verification", "artifact-store"], ["tool-registry", "web"], ["tool-registry", "python"],
  ["tool-registry", "sql"], ["tool-registry", "files"], ["tool-registry", "http"],
  ["scheduler", "researcher"], ["scheduler", "coder"], ["scheduler", "analyst"],
  ["analyst", "critic"], ["researcher", "critic"], ["coder", "critic"],
];

// adjacency for hover highlighting
export const ADJ: Record<string, string[]> = (() => {
  const m: Record<string, string[]> = {};
  for (const n of NODES) m[n.id] = [];
  for (const [a, b] of EDGES) { m[a]?.push(b); m[b]?.push(a); }
  return m;
})();

export const NODE_INDEX: Record<string, number> = Object.fromEntries(NODES.map((n, i) => [n.id, i]));
