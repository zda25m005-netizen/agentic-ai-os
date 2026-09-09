// ---------------------------------------------------------------------------
// Character registry (Phase 2 of the agent-first workspace).
//
// Characters are the PRESENTATION identity of an agent — never the intelligence.
// The real agent behaviour comes from the mission runtime (planner/executor/critic),
// memory engine and tools. A character only carries visual + tone metadata and maps
// an agent's real lifecycle state to an expression.
//
// The registry is data-only so new characters can be added without touching the UI:
// AgentCharacter renders any entry here from its `shape`, `topper`, `eyes` + `accent`.
// Silhouettes are genuinely distinct (aspect ratio + topper + eye style), not recolours.
// ---------------------------------------------------------------------------

// Real agent lifecycle states (mirror the mission/task state machine, plus UI-only
// affordances the runtime can surface: thinking/planning/needs_approval).
export type AgentState =
  | "idle"
  | "thinking"
  | "planning"
  | "working"
  | "waiting"
  | "needs_approval"
  | "completed"
  | "failed"
  | "paused";

export const AGENT_STATES: AgentState[] = [
  "idle", "thinking", "planning", "working",
  "waiting", "needs_approval", "completed", "failed", "paused",
];

// Human-readable label per state (used on cards / detail pages).
export const STATE_LABEL: Record<AgentState, string> = {
  idle: "Idle",
  thinking: "Thinking",
  planning: "Planning",
  working: "Working",
  waiting: "Waiting",
  needs_approval: "Needs approval",
  completed: "Completed",
  failed: "Failed",
  paused: "Paused",
};

export type BodyShape =
  | "round" | "tall" | "bean" | "chunky" | "pear" | "hex"
  | "blob" | "pebble" | "egg" | "capsule" | "dome" | "diamond" | "teardrop";

export type Topper =
  | "none" | "ears" | "antenna" | "antenna2" | "sprout" | "horns"
  | "bow" | "cap" | "fin" | "tuft" | "moon" | "earTufts" | "glasses";

export type EyeStyle = "round" | "oval" | "dot" | "wide" | "sleepy";

export type Personality =
  | "Focused" | "Friendly" | "Analytical" | "Curious" | "Concise" | "Creative";

export interface CharacterDef {
  id: string;
  name: string;
  description: string;   // short personality blurb (presentation only)
  personality: Personality;
  accent: string;        // hex accent colour
  shape: BodyShape;
  topper: Topper;
  eyes: EyeStyle;
}

// 13 characters: the 10 new ones + Peter / Ivy / Rory as members of the same family.
export const CHARACTERS: CharacterDef[] = [
  { id: "nova", name: "Nova", description: "Bright, fast, endlessly curious.", personality: "Curious", accent: "#a78bfa", shape: "diamond", topper: "antenna", eyes: "round" },
  { id: "milo", name: "Milo", description: "Loyal and eager to help.", personality: "Friendly", accent: "#f59e0b", shape: "bean", topper: "ears", eyes: "oval" },
  { id: "luna", name: "Luna", description: "Calm, thoughtful, works at night.", personality: "Analytical", accent: "#6366f1", shape: "dome", topper: "moon", eyes: "sleepy" },
  { id: "atlas", name: "Atlas", description: "Steady and dependable under load.", personality: "Focused", accent: "#38bdf8", shape: "chunky", topper: "horns", eyes: "wide" },
  { id: "coco", name: "Coco", description: "Warm, tidy, keeps things in order.", personality: "Friendly", accent: "#ec4899", shape: "pear", topper: "bow", eyes: "round" },
  { id: "theo", name: "Theo", description: "Methodical planner, one step at a time.", personality: "Concise", accent: "#14b8a6", shape: "tall", topper: "cap", eyes: "dot" },
  { id: "nori", name: "Nori", description: "Fluid, adaptive, goes with the current.", personality: "Creative", accent: "#22c55e", shape: "blob", topper: "fin", eyes: "oval" },
  { id: "echo", name: "Echo", description: "Listens, reflects, connects the dots.", personality: "Analytical", accent: "#06b6d4", shape: "hex", topper: "antenna2", eyes: "round" },
  { id: "momo", name: "Momo", description: "Playful and quick on its feet.", personality: "Creative", accent: "#fb7185", shape: "round", topper: "earTufts", eyes: "round" },
  { id: "pip", name: "Pip", description: "Small, scrappy, always growing.", personality: "Curious", accent: "#84cc16", shape: "pebble", topper: "sprout", eyes: "dot" },
  { id: "peter", name: "Prospect Peter", description: "Scouts new opportunities tirelessly.", personality: "Focused", accent: "#4f8cff", shape: "egg", topper: "cap", eyes: "oval" },
  { id: "ivy", name: "Invoice Ivy", description: "Precise with details and numbers.", personality: "Analytical", accent: "#10b981", shape: "capsule", topper: "tuft", eyes: "round" },
  { id: "rory", name: "Research Rory", description: "Reads deeply and cites everything.", personality: "Analytical", accent: "#fb923c", shape: "teardrop", topper: "glasses", eyes: "round" },
];

export const CHARACTER_MAP: Record<string, CharacterDef> = Object.fromEntries(
  CHARACTERS.map((c) => [c.id, c]),
);

export function getCharacter(id: string | null | undefined): CharacterDef {
  return (id && CHARACTER_MAP[id]) || CHARACTERS[0];
}

// Pick an available character, avoiding those already used where possible.
// Falls back to the least-recently-used ordering the caller provides.
export function pickAvailableCharacter(
  usedIds: string[],
  lruOrder: string[] = [],
): CharacterDef {
  const used = new Set(usedIds);
  const free = CHARACTERS.filter((c) => !used.has(c.id));
  if (free.length) return free[0];
  // all taken → prefer least-recently-used, else first
  for (const id of lruOrder) {
    const c = CHARACTER_MAP[id];
    if (c) return c;
  }
  return CHARACTERS[0];
}
