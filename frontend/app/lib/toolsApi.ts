// ---------------------------------------------------------------------------
// Tools view-model — the capability catalog shown on the Tools page.
//
// The backend has a tool *registry* (app/tools/registry.py) but exposes no HTTP
// API, and there is no per-tool execution telemetry endpoint. This module is the
// single frontend data layer: it defines the 12 product tools with accurate
// descriptions, categories, safety classification, and the agents that use each.
// Execution metrics (runs / success / latency) are intentionally left undefined
// — they are NOT fabricated. When a telemetry endpoint exists, populate the
// optional `telemetry` fields here and the UI will render them automatically.
// Backend tool identifiers (`id`) are never renamed.
// ---------------------------------------------------------------------------

export type ToolStatus = "active" | "disabled" | "restricted" | "error";
export type Category = "Search" | "Knowledge" | "Compute" | "Data" | "Network" | "Agents" | "Analysis";

export interface ToolTelemetry {
  executions: number;
  successRate: number; // 0..1
  avgLatencyMs: number;
  failures: number;
}

export interface ToolView {
  id: string;            // backend identifier — unchanged
  displayName: string;
  description: string;
  category: Category;
  status: ToolStatus;
  safety: string[];      // subtle safety badges
  icon: string;
  agents: string[];      // agents that use this capability (curated association)
  telemetry?: ToolTelemetry; // undefined until a real telemetry API is connected
}

export const CATEGORIES: Category[] = ["Search", "Knowledge", "Compute", "Data", "Network", "Agents", "Analysis"];

export const TOOLS: ToolView[] = [
  { id: "web_search", displayName: "Web Search", category: "Search", icon: "search", status: "active",
    description: "Search external sources for current information.",
    safety: ["External", "Guarded Retrieval"],
    agents: ["Research Agent", "Job Search Agent", "Student Career Agent", "Browser / Action Agent"] },
  { id: "wikipedia", displayName: "Wikipedia", category: "Search", icon: "knowledge", status: "active",
    description: "Retrieve encyclopedia information.",
    safety: ["External", "Read Only"],
    agents: ["Research Agent", "Personal Knowledge Agent"] },
  { id: "rag_search", displayName: "RAG Search", category: "Knowledge", icon: "database", status: "active",
    description: "Retrieve relevant information from connected knowledge.",
    safety: ["Read Only", "Grounded"],
    agents: ["Research Agent", "Personal Knowledge Agent"] },
  { id: "graph_search", displayName: "Graph Search", category: "Knowledge", icon: "agents", status: "active",
    description: "Traverse relationships across graph-based knowledge.",
    safety: ["Read Only", "k-hop"],
    agents: ["Research Agent"] },
  { id: "calculator", displayName: "Calculator", category: "Compute", icon: "calc", status: "active",
    description: "Perform safe mathematical calculations.",
    safety: ["AST Safe"],
    agents: ["Research Agent", "Student Career Agent"] },
  { id: "python_exec", displayName: "Python Execution", category: "Compute", icon: "code", status: "active",
    description: "Execute Python in a sandboxed environment.",
    safety: ["Sandboxed", "Isolated"],
    agents: ["Research Agent"] },
  { id: "data_analysis", displayName: "Data Analysis", category: "Compute", icon: "chart", status: "active",
    description: "Analyze structured and tabular datasets.",
    safety: ["Sandboxed"],
    agents: ["Research Agent"] },
  { id: "sql_tool", displayName: "SQL Query", category: "Data", icon: "database", status: "active",
    description: "Run read-only SQL queries against approved data.",
    safety: ["Read Only"],
    agents: ["Research Agent"] },
  { id: "file_ops", displayName: "File Operations", category: "Data", icon: "file", status: "active",
    description: "Safely read and manage approved files.",
    safety: ["Path-Traversal Safe"],
    agents: ["Personal Knowledge Agent"] },
  { id: "http_tool", displayName: "HTTP Request", category: "Network", icon: "globe", status: "active",
    description: "Make guarded HTTP requests to approved destinations.",
    safety: ["SSRF Safe"],
    agents: ["Job Search Agent", "Browser / Action Agent"] },
  { id: "subagent", displayName: "Subagent Delegation", category: "Agents", icon: "users", status: "active",
    description: "Delegate work to specialized subagents.",
    safety: ["Recursive", "Bounded"],
    agents: ["Research Agent", "Student Career Agent"] },
  { id: "anomaly_scan", displayName: "Anomaly Detection", category: "Analysis", icon: "observability", status: "active",
    description: "Detect anomalies and surface supporting evidence.",
    safety: ["Read Only", "Evidence"],
    agents: ["Research Agent"] },
];

// Swap for `fetch(`${API}/tools`)` when a registry/telemetry endpoint exists.
export async function fetchTools(): Promise<ToolView[]> {
  return TOOLS.map((t) => ({ ...t }));
}

export const hasTelemetry = TOOLS.some((t) => t.telemetry);

export function catalogMetrics(tools: ToolView[]) {
  return {
    total: tools.length,
    active: tools.filter((t) => t.status === "active").length,
    categories: new Set(tools.map((t) => t.category)).size,
    safety: tools.filter((t) => t.safety.length).length,
  };
}
