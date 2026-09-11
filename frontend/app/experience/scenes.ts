// Data for the cinematic landing (World 1). Copy + roster only — the 3D/scroll
// behaviour lives in the components. Kept separate so scenes are easy to tune/extend.

export interface CrewMember {
  id: string;
  name: string;
  role: string;
  line: string;      // playful first-person intro
  img: string;       // transparent mascot cutout
  accent: string;
}

// Uses the real 3D mascot renders (edge-cut to transparent).
export const CREW: CrewMember[] = [
  { id: "peter", name: "Scout", role: "Job / opportunity scout", line: "I search while you sleep.", img: "/mascots/peter-3d-cut.webp", accent: "#6EA8FF" },
  { id: "ivy", name: "Analyst", role: "Data & numbers", line: "Numbers talk to me.", img: "/mascots/ivy-3d-cut.webp", accent: "#F5C542" },
  { id: "rory", name: "Researcher", role: "Literature & synthesis", line: "Give me a question. I'll disappear into the rabbit hole.", img: "/mascots/rory-3d-cut.webp", accent: "#4ADE80" },
  { id: "luna", name: "Memory", role: "Long-term memory", line: "I remember what your other agents forgot.", img: "/mascots/luna-3d-cut.webp", accent: "#8B7DF6" },
];

// Tiny status labels that float around the hero agents.
export const HERO_LABELS = ["RESEARCHING", "CODING", "PLANNING", "REMEMBERING", "SEARCHING", "ANALYZING"];
