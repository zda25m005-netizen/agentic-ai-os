// ---------------------------------------------------------------------------
// Job Search Agent — data layer.
//
// Criteria extraction is REAL and deterministic (the user's own words -> fields,
// no model reasoning shown). Listings are REAL: runJobSearch() calls the backend
// /jobs/search endpoint, which fetches live postings from the official, keyless
// public boards (Greenhouse + Lever) for a curated set of AI/ML companies. No
// job, salary, date, URL or match score is ever fabricated — salary shows only
// when the board discloses it, dates come straight from the board, and Apply
// links are the board's own. Saved jobs + search history persist in localStorage.
// ---------------------------------------------------------------------------
import { API } from "./api";

export interface JobCriteria {
  roles: string[];
  locations: string[];
  experience: string | null;
  remote: boolean;
  keywords: string[];
  raw: string;
}

export interface JobListing {
  id: string;
  title: string;
  company: string;
  location: string | null;
  country: string | null;
  employmentType: string | null;
  experience: string | null;
  experienceMin: number | null;      // required years, from the posting (if stated)
  experienceMax: number | null;
  seniority: string | null;          // "entry" | "senior"
  workplaceType: string | null;      // Remote / Hybrid / Onsite
  salary: string | null;             // null = not disclosed
  salaryType: "disclosed" | "estimated" | null;
  skills: string[];
  description: string;
  postedAt: string | null;           // ISO date from the board, or null
  source: string;
  sourceUrl: string | null;
  applicationUrl: string;            // original application URL (never fabricated)
  matchScore: number | null;         // 0..1 search relevance vs. criteria
  matchBreakdown: Record<string, number>;
  sources: string[];                 // provenance for deduped listings
  // resume-aware personalization (present only when a resume is active)
  candidateScore: number | null;
  candidateBreakdown: Record<string, number>;
  matchedSkills: string[];
  missingSkills: string[];
  matchReason: string | null;
}

export interface SourceStatus {
  source: string;
  status: "ok" | "error";
  count: number;
  note?: string | null;
}

// Authoritative interpretation of the query, returned by the backend so the UI
// chips reflect exactly how the search was constrained.
export interface SearchConstraints {
  role: string | null;
  employmentType: string | null;
  country: string | null;
  city: string | null;
  remote: boolean;
  hybrid: boolean;
  onsite: boolean;
  experience: string | null;
  locationScope: "WORLDWIDE" | "STRICT_COUNTRY" | "STRICT_CITY" | "ANY";
  raw: string;
}

export interface JobSearchResult {
  jobs: JobListing[];
  sources: SourceStatus[];
  constraints: SearchConstraints;
  totalFetched: number;
}

// Chips + count text derived from the interpreted constraints.
export function constraintChips(c: SearchConstraints): string[] {
  const chips: string[] = [];
  if (c.role) chips.push(c.role);
  if (c.employmentType) chips.push(c.employmentType);
  if (c.experience) chips.push(c.experience);
  if (c.remote) chips.push("Remote");
  else if (c.hybrid) chips.push("Hybrid");
  else if (c.onsite) chips.push("Onsite");
  if (c.locationScope === "WORLDWIDE") chips.push("Worldwide");
  else if (c.city) { chips.push(c.city); chips.push("Strict location"); }
  else if (c.country) { chips.push(c.country); chips.push("Strict location"); }
  return chips;
}

export function resultCountText(c: SearchConstraints, n: number): string {
  const word = n === 1 ? "job" : "jobs";
  const role = c.role ? `${c.role} ` : "";
  if (c.locationScope === "WORLDWIDE") return `${n} ${role}${word} found worldwide`;
  if (c.city) return `${n} ${role}${word} found in ${c.city}`;
  if (c.country) return `${n} ${role}${word} found in ${c.country}`;
  return `${n} ${role}${word} found`;
}

// Structured, individually-removable active filters (single source of truth).
export interface FilterSpec {
  role?: string | null;
  country?: string | null;
  city?: string | null;
  experience?: string | null;      // display string, e.g. "0–2 years"
  employmentType?: string | null;
  remote?: boolean;
  worldwide?: boolean;
}

export function filtersFromConstraints(c: SearchConstraints): FilterSpec {
  return {
    role: c.role, country: c.country, city: c.city,
    experience: c.experience, employmentType: c.employmentType,
    remote: c.remote, worldwide: c.locationScope === "WORLDWIDE",
  };
}

// --- real, deterministic criteria extraction --------------------------------
const ROLE_PATTERNS: [string, RegExp][] = [
  ["ML Engineer", /\b(ml|machine[-\s]?learning)\s*engineer/i],
  ["Data Scientist", /\bdata\s*scientist/i],
  ["Data Engineer", /\bdata\s*engineer/i],
  ["AI Engineer", /\bai\s*engineer/i],
  ["Research Scientist", /\b(ml|ai)\s*research|research\s*(scientist|engineer)/i],
  ["MLOps Engineer", /\bmlops/i],
  ["Software Engineer", /\b(software\s*engineer|swe)\b/i],
  ["Intern", /\b(research\s*intern|internship|intern)\b/i],
];
const LOCATIONS = ["Switzerland", "Germany", "Europe", "United States", "USA", "United Kingdom", "UK",
  "Netherlands", "France", "Spain", "Canada", "Ireland", "Zurich", "Geneva", "Berlin", "Munich", "London",
  "Amsterdam", "Paris", "Dublin"];
const SKILLS = ["Python", "PyTorch", "TensorFlow", "JAX", "SQL", "AWS", "GCP", "Azure", "Kubernetes", "Docker",
  "Spark", "Java", "Scala", "C++", "Rust", "Go", "NLP", "Transformers", "RAG", "LLMs", "LLM",
  "Machine Learning", "Deep Learning", "MLOps"];

export function parseCriteria(query: string): JobCriteria {
  const q = query || "";
  const roles: string[] = [];
  for (const [label, re] of ROLE_PATTERNS) if (re.test(q) && !roles.includes(label)) roles.push(label);

  const locations = LOCATIONS.filter((l) => new RegExp(`\\b${l}\\b`, "i").test(q));
  const remote = /\bremote\b/i.test(q);

  let experience: string | null = null;
  if (/\bintern(ship)?\b/i.test(q)) experience = "Internship";
  else if (/fresh\s*grad|new\s*grad|graduate|entry[-\s]?level/i.test(q)) experience = "0–2 years";
  else {
    const m = q.match(/(\d)\s*[-–]\s*(\d)\s*years?/i) || q.match(/(\d)\+?\s*years?/i);
    if (m) experience = m[2] ? `${m[1]}–${m[2]} years` : `${m[1]}+ years`;
  }

  const keywords: string[] = [];
  for (const s of SKILLS) if (new RegExp(`\\b${s.replace("+", "\\+")}\\b`, "i").test(q) && !keywords.includes(s)) keywords.push(s);

  return { roles, locations: [...new Set(locations)], experience, remote, keywords, raw: q.trim() };
}

export function criteriaSummary(c: JobCriteria): string {
  return [c.roles.join(" · "), c.locations.join(", "), c.experience].filter(Boolean).join(" · ") || "Any role";
}

// --- real search: backend fetches live public-board listings ----------------
interface RawJob {
  id: string; title: string; company: string; location: string | null; country: string | null;
  employment_type: string | null; experience: string | null; workplace_type: string | null;
  experience_min: number | null; experience_max: number | null; seniority: string | null;
  salary: string | null; salary_type: string | null; skills: string[]; description: string;
  posted_at: string | null; source: string; source_url: string | null; application_url: string;
  match_score: number | null; match_breakdown: Record<string, number>; sources: string[];
  candidate_score: number | null; candidate_breakdown: Record<string, number>;
  matched_skills: string[]; missing_skills: string[]; match_reason: string | null;
}
interface RawConstraints {
  role: string | null; employment_type: string | null; country: string | null;
  city: string | null; remote: boolean; hybrid: boolean; onsite: boolean;
  experience: string | null; location_scope: SearchConstraints["locationScope"]; raw: string;
}
interface RawResponse {
  jobs: RawJob[];
  sources: SourceStatus[];
  constraints: RawConstraints;
  total_fetched: number;
  total_after_filter: number;
}

function toConstraints(r: RawConstraints): SearchConstraints {
  return {
    role: r.role, employmentType: r.employment_type, country: r.country, city: r.city,
    remote: r.remote, hybrid: r.hybrid, onsite: r.onsite, experience: r.experience,
    locationScope: r.location_scope, raw: r.raw,
  };
}

function toListing(r: RawJob): JobListing {
  return {
    id: r.id, title: r.title, company: r.company, location: r.location, country: r.country,
    employmentType: r.employment_type, experience: r.experience, workplaceType: r.workplace_type,
    experienceMin: r.experience_min ?? null, experienceMax: r.experience_max ?? null, seniority: r.seniority ?? null,
    salary: r.salary, salaryType: (r.salary_type as JobListing["salaryType"]) ?? (r.salary ? "disclosed" : null),
    skills: r.skills || [], description: r.description || "",
    postedAt: r.posted_at, source: r.source, sourceUrl: r.source_url, applicationUrl: r.application_url,
    matchScore: r.match_score, matchBreakdown: r.match_breakdown || {}, sources: r.sources || [r.source],
    candidateScore: r.candidate_score ?? null, candidateBreakdown: r.candidate_breakdown || {},
    matchedSkills: r.matched_skills || [], missingSkills: r.missing_skills || [], matchReason: r.match_reason ?? null,
  };
}

// The raw query is the source of truth — the backend parses + strictly validates.
// `experience` (e.g. "0-2", "3-5", "6+") is an explicit hard constraint from the UI filter.
// `useResume` personalizes ranking with the stored profile (never changes hard filters).
export async function runJobSearch(
  query: string, experience?: string, useResume = false,
): Promise<JobSearchResult> {
  const res = await fetch(`${API}/jobs/search`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    cache: "no-store",
    body: JSON.stringify({ query, limit: 200, experience: experience || null, use_resume: useResume }),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try { const b = await res.json(); if (b?.detail) detail = b.detail; } catch { /* ignore */ }
    throw new Error(detail);
  }
  const data = (await res.json()) as RawResponse;
  return {
    jobs: (data.jobs || []).map(toListing),
    sources: data.sources || [],
    constraints: toConstraints(data.constraints),
    totalFetched: data.total_fetched || 0,
  };
}

// Search from explicit active filters — REPLACES any prior query intent, so a
// removed chip drops exactly that constraint (no stale terms carried over).
export async function runJobSearchFilters(f: FilterSpec, useResume = false): Promise<JobSearchResult> {
  const res = await fetch(`${API}/jobs/search`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    cache: "no-store",
    body: JSON.stringify({
      limit: 200,
      use_resume: useResume,
      filters: {
        role: f.role || null, country: f.country || null, city: f.city || null,
        experience: f.experience || null, employment_type: f.employmentType || null,
        remote: !!f.remote, worldwide: !!f.worldwide,
      },
    }),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try { const b = await res.json(); if (b?.detail) detail = b.detail; } catch { /* ignore */ }
    throw new Error(detail);
  }
  const data = (await res.json()) as RawResponse;
  return {
    jobs: (data.jobs || []).map(toListing),
    sources: data.sources || [],
    constraints: toConstraints(data.constraints),
    totalFetched: data.total_fetched || 0,
  };
}

// --- freshness / salary presentation (never fabricated) ---------------------
export function postedLabel(iso: string | null): string {
  if (!iso) return "Posting date unavailable";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "Posting date unavailable";
  const days = Math.floor((Date.now() - t) / 864e5);
  if (days <= 0) return "Posted today";
  if (days === 1) return "Posted yesterday";
  if (days < 30) return `Posted ${days} days ago`;
  const mo = Math.floor(days / 30);
  return `Posted ${mo} month${mo > 1 ? "s" : ""} ago`;
}

export function salaryLabel(j: JobListing): { text: string; kind: "disclosed" | "estimated" | "none" } {
  if (j.salary && j.salaryType === "estimated") return { text: `${j.salary} (estimated)`, kind: "estimated" };
  if (j.salary) return { text: j.salary, kind: "disclosed" };
  return { text: "Not disclosed", kind: "none" };
}

// --- insights (computed only from real retrieved data) ----------------------
export interface Insights {
  total: number;
  strong: number;
  withSalary: number;
  newThisWeek: number;
  byCountry: [string, number][];
  topSkills: [string, number][];
  companies: number;
}
export function computeInsights(jobs: JobListing[]): Insights {
  const total = jobs.length;
  const strong = jobs.filter((j) => (j.matchScore ?? 0) >= 0.75).length;
  const withSalary = jobs.filter((j) => j.salary).length;
  const weekAgo = Date.now() - 7 * 864e5;
  const newThisWeek = jobs.filter((j) => j.postedAt && Date.parse(j.postedAt) >= weekAgo).length;

  const cc = new Map<string, number>();
  for (const j of jobs) { const k = j.country || "Other"; cc.set(k, (cc.get(k) || 0) + 1); }
  const byCountry = [...cc.entries()].sort((a, b) => b[1] - a[1]);

  const sk = new Map<string, number>();
  for (const j of jobs) for (const s of j.skills) sk.set(s, (sk.get(s) || 0) + 1);
  const topSkills = [...sk.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);

  return {
    total, strong, withSalary, newThisWeek, byCountry, topSkills,
    companies: new Set(jobs.map((j) => j.company)).size,
  };
}

// --- saved jobs (real, per-browser) -----------------------------------------
const SKEY = "jsa.saved.v1";
export function loadSaved(): Record<string, JobListing> {
  try { return JSON.parse(localStorage.getItem(SKEY) || "{}"); } catch { return {}; }
}
export function toggleSaved(job: JobListing): Record<string, JobListing> {
  const map = loadSaved();
  if (map[job.id]) delete map[job.id]; else map[job.id] = job;
  try { localStorage.setItem(SKEY, JSON.stringify(map)); } catch { /* ignore */ }
  return map;
}

// --- local search history (real, per-browser) -------------------------------
export interface SearchHistoryEntry { id: string; query: string; summary: string; at: number; results: number; }
const HKEY = "jsa.history.v1";
export function loadHistory(): SearchHistoryEntry[] {
  try { return JSON.parse(localStorage.getItem(HKEY) || "[]"); } catch { return []; }
}
export function pushHistory(query: string, summary: string, results: number): SearchHistoryEntry[] {
  const list = loadHistory();
  const entry: SearchHistoryEntry = { id: `s${Date.now()}`, query, summary, at: Date.now(), results };
  const next = [entry, ...list.filter((e) => e.query !== query)].slice(0, 12);
  try { localStorage.setItem(HKEY, JSON.stringify(next)); } catch { /* ignore */ }
  return next;
}

export const EXAMPLES = [
  "Find ML Engineer jobs in Switzerland for fresh graduates",
  "Find Data Scientist roles in Germany under 2 years experience",
  "Find AI research internships in Europe",
  "Find remote ML Engineer jobs with Python and PyTorch",
];
