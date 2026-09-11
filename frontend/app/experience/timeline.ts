// Single source of truth for scene ownership. Both the WebGL canvas and the HTML overlay
// read from this so exactly ONE story beat owns the viewport at a time. Scene lengths are
// expressed in vh; bands are derived as fractions of the total scroll so timing stays in
// one place. Continuous world, but never simultaneous scenes.

export type SceneId =
  | "hero" | "t0" | "researcher" | "t1" | "planner" | "t2" | "coder" | "t3"
  | "analyst" | "t4" | "team" | "words" | "comms" | "networkReveal"
  | "networkExplore" | "payoff";

interface SceneDef { id: SceneId; vh: number; solo?: string }

export const SCENES: SceneDef[] = [
  { id: "hero", vh: 120 },
  { id: "t0", vh: 60 },
  { id: "researcher", vh: 160, solo: "researcher" },
  { id: "t1", vh: 50 },
  { id: "planner", vh: 160, solo: "planner" },
  { id: "t2", vh: 50 },
  { id: "coder", vh: 160, solo: "coder" },
  { id: "t3", vh: 50 },
  { id: "analyst", vh: 160, solo: "analyst" },
  { id: "t4", vh: 70 },
  { id: "team", vh: 170 },
  { id: "words", vh: 150 },
  { id: "comms", vh: 190 },
  { id: "networkReveal", vh: 200 },
  { id: "networkExplore", vh: 340 },
  { id: "payoff", vh: 170 },
];

export const TOTAL_VH = SCENES.reduce((s, x) => s + x.vh, 0);

// [start, end] fraction of the master timeline for each scene.
export const BAND: Record<SceneId, [number, number]> = (() => {
  const out = {} as Record<SceneId, [number, number]>;
  let acc = 0;
  for (const s of SCENES) {
    const start = acc / TOTAL_VH;
    acc += s.vh;
    out[s.id] = [start, acc / TOTAL_VH];
  }
  return out;
})();

export const SOLO: Record<string, [number, number]> = Object.fromEntries(
  SCENES.filter((s) => s.solo).map((s) => [s.solo as string, BAND[s.id]]),
);

const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const smooth = (x: number) => x * x * (3 - 2 * x);

// eased 0→1 visibility for a band: fade in over first `fade`, hold, fade out over last `fade`.
export function vis(p: number, band: [number, number], fade = 0.28): number {
  const [s, e] = band;
  if (p <= s || p >= e) return 0;
  const t = (p - s) / (e - s);
  const fin = smooth(clamp01(t / fade));
  const fout = smooth(clamp01((1 - t) / fade));
  return Math.min(fin, fout);
}

// local 0→1 progress within a band (unclamped fade — used for enter/settle motion).
export function local(p: number, band: [number, number]): number {
  const [s, e] = band;
  return clamp01((p - s) / (e - s));
}

// which scene currently owns the viewport (highest vis), for debug + HTML gating.
export function activeScene(p: number): SceneId {
  let best: SceneId = "hero";
  let bestV = -1;
  for (const s of SCENES) {
    const v = p >= BAND[s.id][0] && p < BAND[s.id][1] ? 1 : 0;
    if (v > bestV) { bestV = v; best = s.id; }
  }
  return best;
}
