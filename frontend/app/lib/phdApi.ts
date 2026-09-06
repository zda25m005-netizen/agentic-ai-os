// PhD Finder client. Query or authoritative filters (fresh intent). Reuses the
// shared student profile (scholarships/profile) for eligibility personalization.
import { API } from "./api";
import type { EligibilityCheck } from "./scholarshipsApi";

export interface PhdOpportunity {
  id: string;
  title: string;
  institution: string;
  department: string | null;
  research_group: string | null;
  country: string;
  city: string | null;
  opportunity_type: string;
  fields: string[];
  research_areas: string[];
  supervisor: string | null;
  funding_type: string;
  stipend: string | null;
  salary: string | null;
  application_deadline: string | null;
  deadline_note: string | null;
  start_date: string | null;
  intake: string[];
  description: string;
  language_requirements: string | null;
  source: string;
  official_application_url: string;
  official_university_url: string | null;
  apply_direct: boolean;
  is_verified: boolean;
  last_verified_at: string | null;
  sources: string[];
  match_score: number | null;
  match_breakdown: Record<string, number>;
  match_reason: string | null;
  eligibility_status: string | null;
  eligibility_reasons: string[];
  eligibility_checks: EligibilityCheck[];
  application_checklist: { item: string; kind: string }[];
  tracking_status?: string;
}

export interface PhdIntent {
  raw: string; field: string | null; field_tags: string[]; countries: string[];
  funding: string | null; opportunity_type: string | null; nationality: string | null; intake: string | null;
}
export interface PhdFilterSpec {
  field?: string | null; countries?: string[]; funding?: string | null;
  opportunity_type?: string | null; nationality?: string | null; intake?: string | null;
}
export interface SourceStatus { source: string; status: string; count: number; note?: string | null; }
export interface PhdSearchResult {
  opportunities: PhdOpportunity[]; sources: SourceStatus[]; intent: PhdIntent;
  total_fetched: number; total_after_filter: number; summary: Record<string, number>;
  country_facets: { country: string; count: number }[]; profile_incomplete: boolean;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    method: "POST", headers: { "content-type": "application/json" }, cache: "no-store", body: JSON.stringify(body),
  });
  if (!r.ok) {
    let d = `HTTP ${r.status}`;
    try { const b = await r.json(); if (b?.detail) d = b.detail; } catch { /* ignore */ }
    throw new Error(d);
  }
  return r.json() as Promise<T>;
}

export const searchByQuery = (query: string) => post<PhdSearchResult>("/phd/search", { query });
export const searchByFilters = (filters: PhdFilterSpec) => post<PhdSearchResult>("/phd/search", { filters });
export function filtersFromIntent(i: PhdIntent): PhdFilterSpec {
  return { field: i.field, countries: i.countries, funding: i.funding, opportunity_type: i.opportunity_type, nationality: i.nationality, intake: i.intake };
}
export async function listSaved(): Promise<PhdOpportunity[]> {
  const r = await fetch(`${API}/phd/saved/list`, { cache: "no-store" });
  if (!r.ok) return [];
  return (await r.json()).saved;
}
export const savePhd = (o: PhdOpportunity, status = "Interested") => post("/phd/saved", { opportunity: o, status });
export async function removeSaved(id: string) { await fetch(`${API}/phd/saved/${encodeURIComponent(id)}`, { method: "DELETE" }); }
export const setTrackingStatus = (id: string, status: string) => post(`/phd/saved/${encodeURIComponent(id)}/status`, { status });

export const COUNTRY_OPTIONS = ["Switzerland", "Germany", "Norway", "Netherlands", "Sweden", "United Kingdom", "United States", "Canada", "Australia", "France", "Austria", "Singapore", "Japan", "South Korea", "Europe"];
export const FIELD_OPTIONS = ["Artificial Intelligence", "Computer Science", "Data Science", "Engineering", "Electronics", "Natural Sciences", "Medicine", "Economics", "Social Sciences"];
export const FUNDING_OPTIONS = ["fully_funded", "funded", "salaried", "scholarship", "partial"];
export const OPP_OPTIONS = ["phd_program", "funded_phd_position", "research_position", "fellowship", "doctoral_scholarship"];
export const INTAKE_OPTIONS = ["2026", "2027", "2028"];
export const EXAMPLES = [
  "Fully funded PhD in machine learning in Europe", "PhD positions in computer vision in Germany",
  "AI PhD opportunities in Norway", "Funded PhD in robotics",
];

export function fundingLabel(f: string): string {
  return { fully_funded: "Fully Funded", funded: "Funded", salaried: "Salaried position", scholarship: "Scholarship", partial: "Partially Funded", self_funded: "Self-funded", unknown: "Funding: unknown" }[f] || f;
}
export function oppLabel(t: string): string {
  return { phd_program: "PhD Program", funded_phd_position: "Funded PhD Position", research_position: "Research Position", fellowship: "Fellowship", doctoral_scholarship: "Doctoral Scholarship" }[t] || t;
}
export function eligibilityLabel(s: string | null): { text: string; kind: string } {
  return ({
    eligible: { text: "Eligible", kind: "ok" }, likely: { text: "Likely eligible", kind: "likely" },
    unclear: { text: "Eligibility unclear", kind: "unclear" }, insufficient: { text: "Add profile to check", kind: "unclear" },
    not_eligible: { text: "Not eligible", kind: "no" },
  } as Record<string, { text: string; kind: string }>)[s || "unclear"] || { text: "Eligibility unclear", kind: "unclear" };
}
export function deadlineLabel(o: PhdOpportunity): string {
  if (o.application_deadline) {
    const days = Math.ceil((Date.parse(o.application_deadline) - Date.now()) / 864e5);
    if (Number.isNaN(days)) return o.deadline_note || "See official page";
    if (days < 0) return "Deadline passed";
    if (days <= 30) return `Closing in ${days} day${days === 1 ? "" : "s"}`;
    return `Deadline ${o.application_deadline}`;
  }
  return o.deadline_note || "Deadline not specified";
}
