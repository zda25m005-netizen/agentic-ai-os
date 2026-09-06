// SOP Builder client. Documents + grounded generation + fact-check + quality +
// versions + export. Facts come from the shared profile/résumé; nothing fabricated.
import { API } from "./api";

export interface SopTarget {
  university: string | null; program: string | null; degree: string | null;
  country: string | null; field: string | null;
  opportunity_id: string | null; opportunity_url: string | null; opportunity_description: string | null;
}
export interface SopRequirements {
  word_limit: number | null; char_limit: number | null; prompt: string | null; questions: string[];
}
export interface SopDoc {
  id: string; title: string; target: SopTarget; requirements: SopRequirements;
  style: string; instructions: string; content: string; created_at: number | null; updated_at: number | null;
}
export interface SopVersion { id: string; doc_id: string; label: string; content: string; created_at: number; }
export interface FactClaim { text: string; status: string; note: string; }
export interface FactCheckResult { claims: FactClaim[]; verified: number; needs_verification: number; unsupported: number; }
export interface QualityReport {
  word_count: number; char_count: number; word_limit: number | null; over_limit: boolean;
  coverage: { section: string; covered: boolean }[]; specificity: number;
  generic_flags: string[]; repetition_flags: string[];
}

async function j<T>(path: string, method: string, body?: unknown): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    method, headers: { "content-type": "application/json" }, cache: "no-store",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) {
    let d = `HTTP ${r.status}`;
    try { const b = await r.json(); if (b?.detail) d = b.detail; } catch { /* ignore */ }
    throw new Error(d);
  }
  return r.json() as Promise<T>;
}

export const listSop = async () => (await j<{ documents: unknown[] }>("/sop/list", "GET")).documents as { id: string; title: string; updated_at: number; words: number }[];
export const createSop = (title = "Untitled SOP") => j<SopDoc>("/sop", "POST", { title });
export const fromPhd = (phdId: string) => j<SopDoc>(`/sop/from-phd/${encodeURIComponent(phdId)}`, "POST", {});
export const getSop = (id: string) => j<SopDoc>(`/sop/${id}`, "GET");
export const updateSop = (id: string, patch: Partial<SopDoc>) => j<SopDoc>(`/sop/${id}`, "PUT", patch);
export const deleteSop = (id: string) => j<{ deleted: boolean }>(`/sop/${id}`, "DELETE");
export const generateSop = (id: string, style?: string, instructions?: string) => j<SopDoc>(`/sop/${id}/generate`, "POST", { style, instructions });
export const rewriteSop = (id: string, text: string, action: string) => j<{ text: string }>(`/sop/${id}/rewrite`, "POST", { text, action });
export const checkSop = (id: string) => j<FactCheckResult>(`/sop/${id}/check`, "POST", {});
export const qualitySop = (id: string) => j<QualityReport>(`/sop/${id}/quality`, "GET");
export const listVersions = async (id: string) => (await j<{ versions: SopVersion[] }>(`/sop/${id}/versions`, "GET")).versions;
export const snapshotVersion = (id: string, label: string) => j<SopVersion>(`/sop/${id}/versions`, "POST", { label });
export const restoreVersion = (id: string, vid: string) => j<SopDoc>(`/sop/${id}/versions/${vid}/restore`, "POST", {});

export async function exportSop(id: string, format: string, title: string): Promise<void> {
  const r = await fetch(`${API}/sop/${id}/export`, {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ format }),
  });
  if (!r.ok) throw new Error(`Export failed (HTTP ${r.status})`);
  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const slug = (title || "sop").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  a.href = url; a.download = `${slug}.${format}`; a.click();
  URL.revokeObjectURL(url);
}

export const STYLES = ["academic", "research", "professional", "concise", "personal"];
export const REWRITE_ACTIONS = [
  { key: "concise", label: "Make concise" }, { key: "specific", label: "More specific" },
  { key: "academic", label: "Academic tone" }, { key: "transition", label: "Improve flow" },
  { key: "repetition", label: "Remove repetition" }, { key: "evidence", label: "Flag unsupported" },
];
export function factLabel(s: string): { sym: string; kind: string } {
  return { verified: { sym: "✓", kind: "ok" }, needs_verification: { sym: "⚠", kind: "unclear" }, unsupported: { sym: "✕", kind: "no" } }[s] || { sym: "•", kind: "na" };
}
