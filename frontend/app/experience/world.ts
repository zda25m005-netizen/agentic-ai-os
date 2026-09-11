// ─────────────────────────────────────────────────────────────────────────────
// WORLD 1 — continuous spatial journey (from the first agent introduction onward).
//
// Composition model: every element belongs to a REGION with a focus window in world
// progress w. focusW(w, center, half) is ~1 while that region owns the frame and 0
// otherwise, so exactly ONE hero object + its supporting text are prominent at a time;
// past/future content falls away via focus weight + distance + fog. Nothing above the
// first agent introduction is described here (hero keeps its original camera + timing).
// ─────────────────────────────────────────────────────────────────────────────

import * as THREE from "three";
import { BAND } from "./timeline";

export type V3 = [number, number, number];

export const BOUNDARY = BAND.researcher[0];

// The post-hero spatial world stays completely hidden until the hero has fully left the
// viewport (end of the hero band). ONE activation value gates the entire world so no agent,
// annotation or capability word can ever bleed behind the hero.
export const HERO_EXIT = BAND.hero[1];
export function worldActivation(p: number): number {
  const s = HERO_EXIT, e = HERO_EXIT + 0.02;
  if (p <= s) return 0;
  if (p >= e) return 1;
  const t = (p - s) / (e - s);
  return t * t * (3 - 2 * t);
}

export function toWorld(p: number): number {
  return Math.max(0, Math.min(1, (p - BOUNDARY) / (1 - BOUNDARY)));
}

const smooth = (x: number) => x * x * (3 - 2 * x);

// distance-based visibility: 1 close, 0 far.
export function fade(dist: number, near: number, far: number): number {
  if (dist <= near) return 1;
  if (dist >= far) return 0;
  return smooth(1 - (dist - near) / (far - near));
}

// focus weight: 1 inside [c-half, c+half], easing to 0 over `edge` on each side.
export function focusW(w: number, c: number, half: number, edge = 0.03): number {
  const d = Math.abs(w - c);
  if (d <= half) return 1;
  if (d >= half + edge) return 0;
  return smooth(1 - (d - half) / edge);
}

// 0→1 phase across a focus window (for staged/late reveals within a scene).
export function phaseOf(w: number, c: number, half: number): number {
  return Math.max(0, Math.min(1, (w - (c - half)) / (2 * half)));
}

// ── palette ──────────────────────────────────────────────────────────────────
export const BG = "#07090B";
export const COL = {
  researcher: "#6EE7B7",
  planner: "#7AA2FF",
  coder: "#C6B0FF",
  analyst: "#F5C542",
  word: "#7f8ba1",
  wordDim: "#3f4a63",
  accent: "#9ecbff",
  memory: "#8B7DF6",
  policy: "#F5A97F",
};

// safe area (fraction of viewport) — keep primary text inside this on screen.
export const SAFE = { x: 0.06, top: 0.12, bottom: 0.12 };

// ── region depths (world Z). Camera travels from ~+6 down through these. ────────
export const Z = {
  researcher: -9, planner: -30, coder: -52, analyst: -74, team: -96,
  collaborate: -120, comms: -140, neural: -172, mission: -196, portal: -214,
  brain: -230, memory: -252, governance: -274, artifact: -292, final: -304,
};

export const NEURAL_GROUP_Z = Z.neural;

// ── capability word (spatial landmark around an agent) ──────────────────────────
export interface Cap { t: string; d: V3; s: number; o: number; rot?: [number, number]; late?: boolean }

// ── agents placed physically in the world ──────────────────────────────────────
export interface AgentW {
  id: string; img: string; color: string; pos: V3; scale: number;
  side: "left" | "right" | "center"; focus: number; quote: string; words: Cap[];
  face: V3; // local offset (from the mascot centre) to the mouth/visor — the arrow's endpoint
}

// Focus centers/half-widths come from the rail pacing. Each agent shows only THREE
// primary capability words (+ optional late reveal), spread into depth so they form a
// triangle in space and never out-shout the mascot.
export const AGENT_HALF = 0.028;

export const AGENTS_WORLD: AgentW[] = [
  {
    id: "researcher", img: "/mascots/rory-3d-cut.webp", color: COL.researcher,
    pos: [-3.2, 0.2, Z.researcher], scale: 2.6, side: "left", focus: 0.075, face: [0, 0.55, 0.3],
    quote: "I disappear into the\nrabbit hole so you\ndon't have to.",
    words: [
      { t: "WEB", d: [-4.6, 2.7, -4.5], s: 0.7, o: 0.2, rot: [0, -0.05] },       // far upper-left
      { t: "PAPERS", d: [4.8, 0.3, -1.2], s: 0.95, o: 0.3, rot: [0, 0.09] },     // right, mid depth
      { t: "SOURCES", d: [3.4, -1.9, 1.7], s: 1.05, o: 0.38, rot: [0.04, 0] },   // lower-right, closer
    ],
  },
  {
    id: "planner", img: "/mascots/peter-3d-cut.webp", color: COL.planner,
    pos: [3.6, 0.6, Z.planner], scale: 2.6, side: "right", focus: 0.19, face: [0, 0.6, 0.3],
    quote: "I turn one messy goal\ninto work everyone\ncan execute.",
    words: [
      { t: "GOAL", d: [-4.8, 2.5, -3.5], s: 0.95, o: 0.32, rot: [0, 0.06] },
      { t: "TASKS", d: [-3.2, -0.5, 0.6], s: 1.0, o: 0.36, rot: [0.03, 0] },
      { t: "ROUTES", d: [-5.2, -1.9, -1.5], s: 0.8, o: 0.24, rot: [0, -0.05] },
    ],
  },
  {
    id: "coder", img: "/mascots/ivy-3d-cut.webp", color: COL.coder,
    pos: [-3.8, -0.7, Z.coder], scale: 2.6, side: "left", focus: 0.305, face: [0, 0.5, 0.3],
    quote: "I write it. I run it.\nI break it. I fix it.",
    words: [
      { t: "RUN", d: [3.6, 1.9, -2], s: 0.95, o: 0.34, rot: [0, 0.05] },
      { t: "ERROR", d: [5.0, -0.2, -3.6], s: 0.75, o: 0.22, rot: [0, 0.09] },
      { t: "RETRY", d: [3.0, -1.9, 0.6], s: 0.9, o: 0.3, rot: [0.03, 0] },
      { t: "PASS", d: [4.2, 0.8, 1.6], s: 1.15, o: 0.55, rot: [0, 0], late: true },
    ],
  },
  {
    id: "analyst", img: "/mascots/luna-3d-cut.webp", color: COL.analyst,
    pos: [2.8, -0.4, Z.analyst], scale: 2.6, side: "right", focus: 0.41, face: [0.1, 0.55, 0.3],
    quote: "Give me messy data.\nI'll find the story.",
    words: [
      { t: "DATA", d: [-3.6, 1.9, -2], s: 0.95, o: 0.32, rot: [0, -0.05] },
      { t: "NOISE", d: [-5.0, -0.2, -3.6], s: 0.75, o: 0.2, rot: [0, -0.09] },
      { t: "SIGNAL", d: [-3.0, -1.7, 0.9], s: 0.95, o: 0.38, rot: [0.03, 0] },
      { t: "INSIGHT", d: [-2.6, 2.6, 1.6], s: 1.2, o: 0.55, rot: [0, 0], late: true },
    ],
  },
];

// ── monumental / floating typography — each WINDOWED so one dominates at a time ──
export interface Mon {
  t: string; pos: V3; size: number; color: string;
  anchorX?: "left" | "center" | "right"; opacity?: number;
  fadeFar?: number; win?: [number, number]; rot?: [number, number];
}

// PLAN as a transition monument (appears large just after the planner intro, then passes).
export const MONUMENTS: Mon[] = [
  { t: "PLAN", pos: [3.0, 3.2, Z.planner - 12], size: 6.5, color: "#4a5570", anchorX: "center", fadeFar: 70, win: [0.215, 0.02], rot: [0, 0.04] },

  // floating-words region (team → collaborate): revealed one at a time, well spaced
  { t: "SEARCH", pos: [-9, 3.5, Z.team - 4], size: 3.2, color: COL.wordDim, fadeFar: 52, win: [0.485, 0.008] },
  { t: "CODE", pos: [8, -3.5, Z.team - 10], size: 3.0, color: COL.wordDim, fadeFar: 52, win: [0.51, 0.008] },
  { t: "ANALYZE", pos: [-7, -4, Z.collaborate + 14], size: 3.0, color: COL.wordDim, fadeFar: 52, win: [0.535, 0.008] },

  // THE giant — the only monumental word in its frame; camera weaves between letters
  { t: "COLLABORATE", pos: [0, 0, Z.collaborate], size: 9.5, color: "#5a6478", anchorX: "center", fadeFar: 78, win: [0.568, 0.02] },

  // neural-world landmarks — one at a time as the camera moves inside, low + far
  { t: "TOOLS", pos: [14, -6, Z.neural - 4], size: 6, color: COL.wordDim, fadeFar: 62, win: [0.665, 0.009] },
  { t: "MEMORY", pos: [-16, 3, Z.neural - 12], size: 7, color: COL.wordDim, fadeFar: 66, win: [0.697, 0.009] },
  { t: "PLANNING", pos: [0, 9, Z.neural - 18], size: 6, color: COL.wordDim, anchorX: "center", fadeFar: 66, win: [0.729, 0.009] },
  { t: "EXECUTION", pos: [-6, -9, Z.neural - 8], size: 5, color: COL.wordDim, fadeFar: 60, win: [0.758, 0.009] },
];

// short cinematic phrases through the communication region — sparse, off-centre
export const PHRASES: Mon[] = [
  { t: "THEY DON'T\nWORK ALONE.", pos: [-8, 4.5, Z.comms + 8], size: 1.5, color: COL.word, anchorX: "left", fadeFar: 42, win: [0.61, 0.012] },
  { t: "THEY THINK\nTOGETHER.", pos: [6, -4, Z.comms - 4], size: 1.5, color: COL.accent, anchorX: "left", fadeFar: 42, win: [0.638, 0.012] },
  { t: "YOU STAY\nIN CONTROL.", pos: [0, -6.5, Z.governance + 12], size: 1.6, color: COL.accent, anchorX: "center", fadeFar: 45, win: [0.95, 0.015] },
];

// ── mission runtime ─────────────────────────────────────────────────────────
export const MISSION = {
  brief: "Find funded AI PhD positions\nmatching my profile.",
  pos: [0, 0.5, Z.mission] as V3,
  splits: ["SEARCH", "CHECK", "COMPARE", "RANK", "VERIFY", "REPORT"],
};

export const BRAIN = { center: [0, 0, Z.brain] as V3, parts: ["GOAL", "CONTEXT", "MODEL", "PLANNER", "MEMORY", "TOOLS", "CRITIC", "POLICY"] };

export const MEMORY = {
  center: [0, 0, Z.memory] as V3,
  clusters: [
    { t: "WORKING", d: [-6, 2, 2] as V3, color: "#7dd3fc" },
    { t: "EPISODIC", d: [6, 3, -2] as V3, color: COL.memory },
    { t: "SEMANTIC", d: [-5, -3, -4] as V3, color: "#a5b4fc" },
    { t: "PROCEDURAL", d: [5, -2.5, 3] as V3, color: "#c4b5fd" },
  ],
};

export const GOVERNANCE = {
  gateZ: Z.governance,
  words: [
    { t: "POLICY", pos: [-7, 3, Z.governance - 6] as V3, size: 3.2 },
    { t: "APPROVAL", pos: [0, 5.5, Z.governance - 10] as V3, size: 3.8 },
    { t: "VERIFY", pos: [7, 2.5, Z.governance - 4] as V3, size: 3.0 },
  ],
};

export const ARTIFACT = { center: [0, 0, Z.artifact] as V3, label: "REPORT.PDF" };

// ── final reveal — monumental, spread across the frame, readable at rest ─────────
export const FINAL_WORDS: Mon[] = [
  { t: "BEHIND EVERY", pos: [-15, 5, Z.final + 4], size: 3.0, color: "#c9d3e0", anchorX: "left", fadeFar: 120 },
  { t: "CUTE AGENT", pos: [-15, 1.4, Z.final], size: 5.2, color: "#ffffff", anchorX: "left", fadeFar: 120 },
  { t: "IS A", pos: [7, -1, Z.final - 4], size: 3.0, color: "#c9d3e0", anchorX: "left", fadeFar: 120 },
  { t: "SERIOUS RUNTIME.", pos: [3, -4.6, Z.final - 6], size: 5.0, color: COL.accent, anchorX: "left", fadeFar: 120 },
];

export const LINKS: { from: string; to: V3; label: string; color: string }[] = [
  { from: "researcher", to: AGENTS_WORLD[1].pos, label: "SOURCES", color: COL.researcher },
  { from: "planner", to: AGENTS_WORLD[2].pos, label: "TASK", color: COL.planner },
  { from: "coder", to: AGENTS_WORLD[3].pos, label: "RESULT", color: COL.coder },
  { from: "analyst", to: [0, 0, Z.comms], label: "INSIGHT", color: COL.analyst },
];

// ─────────────────────────────────────────────────────────────────────────────
// CAMERA RAIL — smooth Catmull-Rom path; uneven w spacing sets the pacing.
// ─────────────────────────────────────────────────────────────────────────────
export interface RailPoint { w: number; pos: V3; look: V3 }

export const RAIL: RailPoint[] = [
  { w: 0.00, pos: [-0.9, 0.06, 6.4], look: [-1.0, 0.17, 0] },
  { w: 0.05, pos: [-1.2, 0.25, -1], look: [-3.0, 0.2, Z.researcher] },
  { w: 0.09, pos: [-0.9, 0.35, -4], look: [-3.2, 0.2, Z.researcher] },
  { w: 0.12, pos: [0.7, 0.35, -14], look: [2.4, 0.5, Z.planner] },
  { w: 0.17, pos: [2.1, 0.5, -23], look: [3.6, 0.6, Z.planner] },
  { w: 0.20, pos: [3.3, 0.6, -26], look: [3.6, 0.6, Z.planner] },
  { w: 0.24, pos: [1.0, 0.1, -38], look: [-3.0, -0.5, Z.coder] },
  { w: 0.29, pos: [-2.2, -0.6, -46], look: [-3.8, -0.7, Z.coder] },
  { w: 0.31, pos: [-3.3, -0.7, -49], look: [-3.8, -0.7, Z.coder] },
  { w: 0.35, pos: [-0.6, -0.5, -62], look: [2.4, -0.4, Z.analyst] },
  { w: 0.40, pos: [1.6, -0.4, -70], look: [2.8, -0.4, Z.analyst] },
  { w: 0.42, pos: [2.5, -0.35, -72], look: [2.8, -0.4, Z.analyst] },
  { w: 0.47, pos: [0, 1.4, -84], look: [0, 0, Z.team] },
  { w: 0.49, pos: [0, 2.1, -86], look: [0, 0, Z.team] },
  { w: 0.53, pos: [0, 0.6, -104], look: [0, 0, Z.collaborate] },
  { w: 0.57, pos: [-1.2, 0, -116], look: [1.2, 0, Z.collaborate - 6] },
  { w: 0.60, pos: [0.6, 0, -126], look: [0, 0, Z.comms] },
  { w: 0.63, pos: [0, 0, -134], look: [0, 0, Z.comms - 10] },
  { w: 0.66, pos: [0, 0.4, -150], look: [0, 0, Z.neural] },
  { w: 0.70, pos: [0, 0.3, -162], look: [0, 0, Z.neural] },
  { w: 0.74, pos: [0.4, 0.2, -168], look: [0, 0, Z.neural - 4] },
  { w: 0.77, pos: [0, 0.4, -182], look: [0, 0.5, Z.mission] },
  { w: 0.80, pos: [0, 0.5, -190], look: [0, 0.5, Z.mission - 2] },
  { w: 0.83, pos: [-1.0, 0, -200], look: [-2.5, 0, Z.portal] },
  { w: 0.86, pos: [0, 0, -208], look: [0, 0, Z.portal] },
  { w: 0.88, pos: [0, 0, Z.portal], look: [0, 0, Z.brain] },
  { w: 0.90, pos: [0, 0, -224], look: [0, 0, Z.brain] },
  { w: 0.92, pos: [0, 0.3, -240], look: [0, 0, Z.memory] },
  { w: 0.935, pos: [0, 0.2, -247], look: [0, 0, Z.memory] },
  { w: 0.95, pos: [0, 0, -266], look: [0, 0, Z.governance] },
  { w: 0.962, pos: [0, 0, -270], look: [0, 0, Z.governance] },
  { w: 0.972, pos: [0, 0, -284], look: [0, 0, Z.artifact] },
  { w: 0.985, pos: [0, 1.4, -292], look: [0, 0, Z.artifact - 4] },
  { w: 0.995, pos: [0, 8, -284], look: [0, -2, Z.final] },
  { w: 1.00, pos: [0, 17, -252], look: [0, -2, Z.final] },
];

const CURVE = new THREE.CatmullRomCurve3(
  RAIL.map((r) => new THREE.Vector3(r.pos[0], r.pos[1], r.pos[2])),
  false, "catmullrom", 0.5,
);

export function sampleRail(w: number, outPos: THREE.Vector3, outLook: THREE.Vector3): void {
  const n = RAIL.length;
  let i = 0;
  while (i < n - 2 && w > RAIL[i + 1].w) i++;
  const a = RAIL[i], b = RAIL[i + 1];
  const localT = Math.max(0, Math.min(1, (w - a.w) / ((b.w - a.w) || 1)));
  const e = smooth(localT);
  const u = Math.max(0, Math.min(1, (i + e) / (n - 1)));
  CURVE.getPoint(u, outPos);
  outLook.set(
    a.look[0] + (b.look[0] - a.look[0]) * e,
    a.look[1] + (b.look[1] - a.look[1]) * e,
    a.look[2] + (b.look[2] - a.look[2]) * e,
  );
}

// which region owns the frame at world progress w (for the composition debug HUD).
export function regionAt(w: number): string {
  const r: [number, string][] = [
    [0.11, "researcher"], [0.16, "→ planner"], [0.22, "planner"], [0.27, "→ coder"],
    [0.33, "coder"], [0.38, "→ analyst"], [0.44, "analyst"], [0.52, "team"],
    [0.585, "collaborate"], [0.64, "communication"], [0.78, "neural network"],
    [0.855, "mission"], [0.905, "brain"], [0.945, "memory"], [0.968, "governance"],
    [0.99, "artifact"], [1.01, "final runtime"],
  ];
  for (const [hi, name] of r) if (w < hi) return name;
  return "final runtime";
}
