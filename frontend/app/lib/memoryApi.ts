// ---------------------------------------------------------------------------
// Memory data abstraction — the SINGLE integration point for the Memory page.
//
// The backend memory subsystem (app/memory: multilayer / manager / dynamics)
// is not yet exposed over HTTP. Until a GET/PUT/DELETE `/memories` API exists,
// this module serves realistic *sample* records so the UI is fully functional.
// Mutations (edit / pin / forget / add) update an in-memory store for the
// current session only — they are NOT persisted. When the backend endpoints
// land, replace the bodies below with fetch() calls; the component tree does
// not need to change.
// ---------------------------------------------------------------------------

export type Layer = "working" | "episodic" | "semantic" | "procedural" | "organizational";

export const LAYERS: { id: Layer; name: string; desc: string }[] = [
  { id: "working", name: "Working", desc: "Short-term scratchpad, capacity-bounded (evicts oldest)." },
  { id: "episodic", name: "Episodic", desc: "Append-only log of what happened, in time order." },
  { id: "semantic", name: "Semantic", desc: "Durable keyed facts (re-learning updates in place)." },
  { id: "procedural", name: "Procedural", desc: "Learned 'how-to' step sequences." },
  { id: "organizational", name: "Organizational", desc: "Knowledge shared across missions." },
];

export interface MemoryRecord {
  id: string;
  layer: Layer;
  content: string;
  importance: number; // 0..1
  strength: number;   // 0..1 (decay state; higher = fresher/reinforced)
  createdAt: string;  // ISO date
  lastRetrieved: string | null; // ISO datetime
  retrievals: number;
  source: string;     // agent that created/uses it
  mission?: { id: number; title: string };
  tags: string[];
  pinned: boolean;
}

export interface Consolidation { from: Layer; to: Layer; note: string; at: string; }
export interface Conflict { id: string; topic: string; memoryIds: string[]; }

const now = Date.now();
const days = (n: number) => new Date(now - n * 864e5).toISOString();
const hours = (n: number) => new Date(now - n * 36e5).toISOString();

// Realistic sample set — consistent counts, real provenance, no fabricated internals.
const SAMPLE: MemoryRecord[] = [
  { id: "m1", layer: "semantic", content: "User prefers Switzerland for AI/ML PhD opportunities.",
    importance: 0.94, strength: 0.88, createdAt: days(6), lastRetrieved: hours(2), retrievals: 14,
    source: "Personal Knowledge Agent", mission: { id: 3, title: "PhD Search — Switzerland" },
    tags: ["PhD", "Switzerland", "AI/ML"], pinned: true },
  { id: "m2", layer: "episodic", content: "Compared ETH Zürich and EPFL doctoral funding structures.",
    importance: 0.71, strength: 0.64, createdAt: days(4), lastRetrieved: days(1), retrievals: 5,
    source: "Research Agent", mission: { id: 3, title: "PhD Search — Switzerland" },
    tags: ["PhD", "Switzerland", "Universities"], pinned: false },
  { id: "m3", layer: "procedural", content: "Workflow for generating professional research reports (search → filter → verify → score → recommend).",
    importance: 0.83, strength: 0.79, createdAt: days(5), lastRetrieved: hours(3), retrievals: 22,
    source: "Research Agent", mission: { id: 6, title: "Compare RAG vs Fine-tuning" },
    tags: ["Research", "PDF", "Workflow"], pinned: true },
  { id: "m4", layer: "semantic", content: "RAG grounds generation in retrieved documents; strongest for freshness and citations.",
    importance: 0.8, strength: 0.72, createdAt: days(3), lastRetrieved: hours(5), retrievals: 9,
    source: "Research Agent", mission: { id: 6, title: "Compare RAG vs Fine-tuning" },
    tags: ["RAG", "Retrieval", "LLM"], pinned: false },
  { id: "m5", layer: "semantic", content: "Fine-tuning bakes knowledge into weights; costly to update, best for behaviour adaptation.",
    importance: 0.68, strength: 0.55, createdAt: days(3), lastRetrieved: days(2), retrievals: 6,
    source: "Research Agent", mission: { id: 6, title: "Compare RAG vs Fine-tuning" },
    tags: ["Fine-tuning", "LLM"], pinned: false },
  { id: "m6", layer: "working", content: "Shortlist: ML Engineer roles at DeepMind, Mistral, Cohere — awaiting salary data.",
    importance: 0.42, strength: 0.31, createdAt: hours(6), lastRetrieved: hours(1), retrievals: 3,
    source: "Job Search Agent", mission: { id: 1, title: "Find ML Jobs in Germany" },
    tags: ["Jobs", "Shortlist"], pinned: false },
  { id: "m7", layer: "working", content: "Draft cover-letter angle: emphasise evidence-first research tooling.",
    importance: 0.35, strength: 0.22, createdAt: hours(9), lastRetrieved: hours(8), retrievals: 1,
    source: "Student Career Agent", tags: ["Resume", "Draft"], pinned: false },
  { id: "m8", layer: "episodic", content: "Generated resume v3 for ML Engineer applications and exported PDF.",
    importance: 0.58, strength: 0.6, createdAt: days(1), lastRetrieved: hours(1), retrievals: 4,
    source: "Student Career Agent", mission: { id: 1, title: "Find ML Jobs in Germany" },
    tags: ["Resume", "PDF"], pinned: false },
  { id: "m9", layer: "procedural", content: "Interview prep loop: role research → competency map → mock Q&A → feedback.",
    importance: 0.64, strength: 0.5, createdAt: days(7), lastRetrieved: days(3), retrievals: 7,
    source: "Student Career Agent", tags: ["Interview", "Workflow"], pinned: false },
  { id: "m10", layer: "organizational", content: "House report style: no AI-internals, evidence-linked findings, honest confidence labels.",
    importance: 0.9, strength: 0.85, createdAt: days(9), lastRetrieved: hours(4), retrievals: 31,
    source: "Research Agent", tags: ["Standards", "Reporting"], pinned: true },
  { id: "m11", layer: "organizational", content: "Preferred citation format: authors (year). Title. Venue — with arXiv/DOI ids.",
    importance: 0.62, strength: 0.44, createdAt: days(8), lastRetrieved: days(4), retrievals: 8,
    source: "Research Agent", tags: ["Citations", "Standards"], pinned: false },
  { id: "m12", layer: "episodic", content: "Structured Memory scored highest overall in the LLM-memory comparison.",
    importance: 0.55, strength: 0.28, createdAt: days(2), lastRetrieved: days(2), retrievals: 2,
    source: "Research Agent", mission: { id: 8, title: "Evaluate LLM memory approaches" },
    tags: ["Memory", "Evaluation"], pinned: false },
];

// A conflict exists only when two memories disagree on the same topic. Empty by
// default; populate here to exercise the ConflictIndicator.
const CONFLICTS: Conflict[] = [];

const CONSOLIDATIONS: Consolidation[] = [
  { from: "working", to: "semantic", note: "Research notes consolidated into durable knowledge.", at: hours(2) },
  { from: "working", to: "procedural", note: "Repeated report steps promoted to a reusable workflow.", at: hours(7) },
  { from: "episodic", to: "organizational", note: "Reporting standard shared across missions.", at: days(1) },
];

let store: MemoryRecord[] | null = null;
const load = () => (store ??= SAMPLE.map((m) => ({ ...m, tags: [...m.tags] })));

export interface MemorySnapshot {
  records: MemoryRecord[];
  consolidations: Consolidation[];
  conflicts: Conflict[];
}

// Swap this body for `fetch(`${API}/memories`)` when the endpoint exists.
export async function fetchMemory(): Promise<MemorySnapshot> {
  return { records: load().map((m) => ({ ...m })), consolidations: CONSOLIDATIONS, conflicts: CONFLICTS };
}

export function updateMemory(id: string, patch: Partial<MemoryRecord>): MemoryRecord[] {
  const db = load();
  const i = db.findIndex((m) => m.id === id);
  if (i >= 0) db[i] = { ...db[i], ...patch };
  return db.map((m) => ({ ...m }));
}
export function forgetMemory(id: string): MemoryRecord[] {
  store = load().filter((m) => m.id !== id);
  return store.map((m) => ({ ...m }));
}
export function addMemory(): { records: MemoryRecord[]; id: string } {
  const db = load();
  const id = `m${Date.now()}`;
  db.unshift({
    id, layer: "working", content: "", importance: 0.3, strength: 0.3,
    createdAt: new Date().toISOString(), lastRetrieved: null, retrievals: 0,
    source: "You", tags: [], pinned: false,
  });
  return { records: db.map((m) => ({ ...m })), id };
}
export function togglePin(id: string): MemoryRecord[] {
  const db = load();
  const m = db.find((x) => x.id === id);
  if (m) m.pinned = !m.pinned;
  return db.map((x) => ({ ...x }));
}

// ---- derived, always consistent with the current record set ----
export const isLongTerm = (l: Layer) => l !== "working";

export function metrics(records: MemoryRecord[]) {
  const today = new Date(); today.setHours(0, 0, 0, 0);
  return {
    total: records.length,
    working: records.filter((m) => m.layer === "working").length,
    longTerm: records.filter((m) => isLongTerm(m.layer)).length,
    retrievedToday: records.filter((m) => m.lastRetrieved && new Date(m.lastRetrieved) >= today).length,
  };
}
export function layerCounts(records: MemoryRecord[]): Record<Layer, number> {
  const c = { working: 0, episodic: 0, semantic: 0, procedural: 0, organizational: 0 } as Record<Layer, number>;
  records.forEach((m) => { c[m.layer]++; });
  return c;
}

export function relativeTime(iso: string | null): string {
  if (!iso) return "never";
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 6e4), h = Math.floor(diff / 36e5), d = Math.floor(diff / 864e5);
  if (m < 1) return "just now";
  if (h < 1) return `${m}m ago`;
  if (d < 1) return `${h}h ago`;
  if (d === 1) return "yesterday";
  return `${d}d ago`;
}
export function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}
