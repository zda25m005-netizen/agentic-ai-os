// Resume profile client. The resume is parsed server-side (LLM) and only the
// structured profile is stored — never in the browser. Uploading a resume sends
// its text to the configured model for analysis (the user's explicit choice).
import { API } from "./api";

export interface ResumeProfile {
  skills: string[];
  job_titles: string[];
  experience_years: number | null;
  education: string[];
  projects: string[];
  certifications: string[];
  industries: string[];
  locations: string[];
  languages: string[];
  summary: string;
}

export interface ResumeState {
  exists: boolean;
  filename?: string | null;
  uploaded_at?: number | null;
  profile?: ResumeProfile | null;
  sparse?: boolean;
  suggested_roles?: string[];
}

async function fileToBase64(file: File): Promise<string> {
  const buf = new Uint8Array(await file.arrayBuffer());
  let bin = "";
  for (let i = 0; i < buf.length; i++) bin += String.fromCharCode(buf[i]);
  return btoa(bin);
}

async function handle(res: Response): Promise<ResumeState> {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try { const b = await res.json(); if (b?.detail) detail = b.detail; } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json() as Promise<ResumeState>;
}

export async function getResume(): Promise<ResumeState> {
  return handle(await fetch(`${API}/resume`, { cache: "no-store" }));
}

export async function uploadResume(file: File): Promise<ResumeState> {
  const content_b64 = await fileToBase64(file);
  return handle(await fetch(`${API}/resume`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ filename: file.name, content_b64 }),
  }));
}

export async function removeResume(): Promise<void> {
  await fetch(`${API}/resume`, { method: "DELETE" });
}

export function experienceLabel(years: number | null | undefined): string {
  if (years == null) return "Not specified";
  if (years <= 0.5) return "Entry level";
  return `${years % 1 === 0 ? years : years.toFixed(1)} years`;
}
