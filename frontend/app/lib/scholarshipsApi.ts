// Scholarship Finder client. Query OR structured filters (filters are
// authoritative and reset the intent — no stale filters carry over). The resume
// only personalizes ranking. Fields mirror the backend JSON (snake_case).
import { API } from "./api";

export interface Scholarship {
  id: string;
  title: string;
  provider: string;
  institution: string | null;
  country: string;
  countries: string[];
  degree_levels: string[];
  fields: string[];
  scholarship_type: string | null;
  funding_type: string;
  tuition_coverage: boolean | null;
  stipend: string | null;
  deadline: string | null;
  deadline_note: string | null;
  intake: string[];
  duration: string | null;
  description: string;
  language_requirements: string | null;
  academic_requirements: string | null;
  work_experience_requirement: string | null;
  nationality_note: string | null;
  source: string;
  source_url: string | null;
  application_url: string;
  official_provider_url: string | null;
  apply_direct: boolean;
  is_verified: boolean;
  last_verified_at: string | null;
  sources: string[];
  match_score: number | null;
  match_breakdown: Record<string, number>;
  match_reason: string | null;
  eligibility_status: string | null;
  eligibility_reasons: string[];
  tracking_status?: string;
}

export interface Intent {
  raw: string;
  field: string | null;
  field_tags: string[];
  countries: string[];
  degree: string | null;
  funding: string | null;
  nationality: string | null;
  intake: string | null;
  scholarship_type: string | null;
  no_ielts: boolean;
}

export interface SourceStatus { source: string; status: string; count: number; note?: string | null; }

export interface FilterSpec {
  field?: string | null;
  countries?: string[];
  degree?: string | null;
  funding?: string | null;
  nationality?: string | null;
  intake?: string | null;
  scholarship_type?: string | null;
  no_ielts?: boolean;
}

export interface SearchResult {
  scholarships: Scholarship[];
  sources: SourceStatus[];
  intent: Intent;
  total_fetched: number;
  total_after_filter: number;
  summary: Record<string, number>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    method: "POST", headers: { "content-type": "application/json" },
    cache: "no-store", body: JSON.stringify(body),
  });
  if (!r.ok) {
    let detail = `HTTP ${r.status}`;
    try { const b = await r.json(); if (b?.detail) detail = b.detail; } catch { /* ignore */ }
    throw new Error(detail);
  }
  return r.json() as Promise<T>;
}

export function searchByQuery(query: string, useResume = false): Promise<SearchResult> {
  return post<SearchResult>("/scholarships/search", { query, use_resume: useResume, limit: 100 });
}
export function searchByFilters(filters: FilterSpec, useResume = false): Promise<SearchResult> {
  return post<SearchResult>("/scholarships/search", { filters, use_resume: useResume, limit: 100 });
}

export async function listSaved(): Promise<Scholarship[]> {
  const r = await fetch(`${API}/scholarships/saved`, { cache: "no-store" });
  if (!r.ok) return [];
  return (await r.json()).saved as Scholarship[];
}
export function saveScholarship(s: Scholarship, status = "Interested") {
  return post("/scholarships/saved", { scholarship: s, status });
}
export function setTrackingStatus(id: string, status: string) {
  return post(`/scholarships/saved/${encodeURIComponent(id)}/status`, { status });
}
export async function removeSaved(id: string) {
  await fetch(`${API}/scholarships/saved/${encodeURIComponent(id)}`, { method: "DELETE" });
}

// Build an authoritative FilterSpec from a returned intent (for chip removal).
export function filtersFromIntent(i: Intent): FilterSpec {
  return {
    field: i.field, countries: i.countries, degree: i.degree, funding: i.funding,
    nationality: i.nationality, intake: i.intake, scholarship_type: i.scholarship_type, no_ielts: i.no_ielts,
  };
}

export const COUNTRY_OPTIONS = [
  "Switzerland", "Germany", "Norway", "United Kingdom", "United States", "Canada",
  "Australia", "Netherlands", "Sweden", "Finland", "France", "Italy", "Denmark",
  "Austria", "Belgium", "Ireland", "Japan", "South Korea", "Singapore", "New Zealand", "Europe",
];
export const DEGREE_OPTIONS = ["bachelor", "master", "phd", "postdoc", "diploma"];
export const FUNDING_OPTIONS = ["fully_funded", "partial", "tuition", "stipend"];
export const FIELD_OPTIONS = [
  "Artificial Intelligence", "Computer Science", "Data Science", "Engineering", "Electronics",
  "Business", "Finance", "Economics", "Management", "Medicine", "Law", "Social Sciences",
  "Natural Sciences", "Humanities", "Arts",
];
export const TYPE_OPTIONS = ["government", "university", "research", "fellowship", "exchange"];
export const INTAKE_OPTIONS = ["2026", "2027", "2028"];

export const EXAMPLES = [
  "Fully funded Master's in Switzerland",
  "PhD scholarships in Norway",
  "Scholarships for Indian students in Germany",
  "AI scholarships for 2027",
  "Fully funded engineering scholarships",
];

export function fundingLabel(f: string): string {
  return { fully_funded: "Fully Funded", partial: "Partially Funded", tuition: "Tuition", stipend: "Stipend" }[f] || f;
}
export function degreeLabel(d: string): string {
  return { bachelor: "Bachelor's", master: "Master's", phd: "PhD", postdoc: "Postdoc", diploma: "Diploma" }[d] || d;
}
export function eligibilityLabel(s: string | null): { text: string; kind: string } {
  const map: Record<string, { text: string; kind: string }> = {
    eligible: { text: "Eligible", kind: "ok" },
    likely: { text: "Likely eligible", kind: "likely" },
    unclear: { text: "Eligibility unclear", kind: "unclear" },
    not_eligible: { text: "Not eligible", kind: "no" },
  };
  return map[s || "unclear"] || map.unclear;
}
