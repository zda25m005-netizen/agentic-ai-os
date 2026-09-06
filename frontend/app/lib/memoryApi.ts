// ---------------------------------------------------------------------------
// Memory data layer — now backed by the REAL /memory API (MemoryOrchestrator).
//
// Records are fetched from the backend and cached locally. Mutations update the
// cache synchronously (so the existing components keep their optimistic, sync
// contract) and persist to the backend in the background. No sample/fabricated
// data — an empty store simply shows an empty state.
// ---------------------------------------------------------------------------
import { API } from "./api";

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
  importance: number;
  strength: number;
  confidence?: number;
  status?: string;
  provenance?: string | null;
  createdAt: string;
  lastRetrieved: string | null;
  retrievals: number;
  source: string;
  mission?: { id: number; title: string };
  tags: string[];
  pinned: boolean;
}

export interface Consolidation { from: Layer; to: Layer; note: string; at: string; }
export interface Conflict { id: string; topic: string; memoryIds: string[]; }
export interface MemorySnapshot {
  records: MemoryRecord[];
  consolidations: Consolidation[];
  conflicts: Conflict[];
}

let store: MemoryRecord[] = [];

interface RawUi {
  id: string; layer: Layer; content: string; importance: number; strength: number;
  confidence?: number; status?: string; provenance?: string | null;
  createdAt: string | null; lastRetrieved: string | null; retrievals: number;
  source: string; mission?: { id: number; title: string } | null; tags: string[]; pinned: boolean;
}
const toRecord = (r: RawUi): MemoryRecord => ({
  id: r.id, layer: r.layer, content: r.content, importance: r.importance, strength: r.strength,
  confidence: r.confidence, status: r.status, provenance: r.provenance,
  createdAt: r.createdAt || new Date().toISOString(), lastRetrieved: r.lastRetrieved,
  retrievals: r.retrievals, source: r.source, mission: r.mission || undefined,
  tags: r.tags || [], pinned: r.pinned,
});

export async function fetchMemory(): Promise<MemorySnapshot> {
  try {
    const r = await fetch(`${API}/memory/list`, { cache: "no-store" });
    const data = await r.json();
    store = (data.memories || []).map(toRecord);
  } catch {
    store = [];
  }
  // The backend does not emit fabricated consolidation/conflict analytics yet.
  return { records: store.map((m) => ({ ...m })), consolidations: [], conflicts: [] };
}

const isTemp = (id: string) => !id.startsWith("mem-");

export function updateMemory(id: string, patch: Partial<MemoryRecord>): MemoryRecord[] {
  const i = store.findIndex((m) => m.id === id);
  if (i >= 0) store[i] = { ...store[i], ...patch };
  if (isTemp(id)) {
    // first save of a locally-created draft -> create it on the backend
    const rec = store[i];
    fetch(`${API}/memory`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ content: rec?.content ?? "", layer: rec?.layer ?? "working",
        tags: rec?.tags ?? [], source: "user", pinned: rec?.pinned ?? false }),
    }).then((r) => r.json()).then((res) => {
      if (res?.memory?.id && i >= 0) store[i] = { ...store[i], id: res.memory.id };
    }).catch(() => {});
  } else {
    fetch(`${API}/memory/${id}`, {
      method: "PUT", headers: { "content-type": "application/json" },
      body: JSON.stringify({ content: patch.content, tags: patch.tags, importance: patch.importance, pinned: patch.pinned }),
    }).catch(() => {});
  }
  return store.map((m) => ({ ...m }));
}

export function forgetMemory(id: string): MemoryRecord[] {
  store = store.filter((m) => m.id !== id);
  if (!isTemp(id)) fetch(`${API}/memory/${id}/forget`, { method: "POST" }).catch(() => {});
  return store.map((m) => ({ ...m }));
}

export function togglePin(id: string): MemoryRecord[] {
  const m = store.find((x) => x.id === id);
  if (m) {
    m.pinned = !m.pinned;
    if (!isTemp(id)) fetch(`${API}/memory/${id}`, {
      method: "PUT", headers: { "content-type": "application/json" },
      body: JSON.stringify({ pinned: m.pinned }),
    }).catch(() => {});
  }
  return store.map((x) => ({ ...x }));
}

export function addMemory(): { records: MemoryRecord[]; id: string } {
  const id = `draft-${Date.now()}`; // temp id; persisted on first save
  store.unshift({
    id, layer: "working", content: "", importance: 0.3, strength: 0.3,
    createdAt: new Date().toISOString(), lastRetrieved: null, retrievals: 0,
    source: "You", tags: [], pinned: false,
  });
  return { records: store.map((m) => ({ ...m })), id };
}

// ---- derived helpers (unchanged) ------------------------------------------
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
