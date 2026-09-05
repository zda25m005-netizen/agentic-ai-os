"use client";
import { useState } from "react";
import Icon from "../Icon";
import {
  StudentProfile, saveProfile, prefillProfile, clearProfile, profileIsEmpty,
  FIELD_OPTIONS, DEGREE_OPTIONS, degreeLabel,
} from "../../lib/scholarshipsApi";

const EMPTY: StudentProfile = {
  nationality: null, degree: null, field: null, field_tags: [], gpa: null, gpa_scale: null,
  graduation_year: null, ielts: null, toefl: null, experience_years: null, skills: [], preferred_countries: [],
};

export default function StudentProfilePanel({ profile, onChange, hasResume }: {
  profile: StudentProfile | null; onChange: (p: StudentProfile) => void; hasResume: boolean;
}) {
  const p = profile || EMPTY;
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<StudentProfile>(p);
  const [busy, setBusy] = useState(false);

  const empty = profileIsEmpty(profile);

  const startEdit = () => { setDraft(profile || EMPTY); setEditing(true); };
  const num = (v: string): number | null => (v.trim() === "" ? null : Number(v));

  const save = async () => {
    setBusy(true);
    try { onChange(await saveProfile(draft)); setEditing(false); } finally { setBusy(false); }
  };
  const prefill = async () => {
    setBusy(true);
    try { const r = await prefillProfile(); if (r) setDraft(r); } finally { setBusy(false); }
  };
  const wipe = async () => { await clearProfile(); onChange(EMPTY); setEditing(false); };

  if (!editing) {
    return (
      <div className="profile">
        <div className="profile-head">
          <span className="sec-h" style={{ margin: 0 }}>Your profile</span>
          <button className="btn ghost sm" onClick={startEdit}>{empty ? "Complete profile" : "Edit"}</button>
        </div>
        {empty ? (
          <div className="profile-empty">
            Add your nationality, degree, field, GPA and test scores so eligibility can be checked against
            each scholarship&apos;s real requirements. Nothing is assumed — unknown fields show as “verify”.
          </div>
        ) : (
          <div className="profile-summary">
            {p.nationality && <span className="pv">{p.nationality}</span>}
            {p.degree && <span className="pv">{degreeLabel(p.degree)}</span>}
            {p.field && <span className="pv">{p.field}</span>}
            {p.gpa != null && <span className="pv">GPA {p.gpa}{p.gpa_scale ? `/${p.gpa_scale}` : ""}</span>}
            {p.ielts != null && <span className="pv">IELTS {p.ielts}</span>}
            {p.experience_years != null && <span className="pv">{p.experience_years}y exp</span>}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="profile editing">
      <div className="profile-head">
        <span className="sec-h" style={{ margin: 0 }}>Your profile</span>
        <div style={{ display: "flex", gap: 6 }}>
          {hasResume && <button className="btn ghost sm" onClick={prefill} disabled={busy}>Prefill from résumé</button>}
          <button className="btn ghost sm" onClick={() => setEditing(false)}>Cancel</button>
          <button className="btn primary sm" onClick={save} disabled={busy}>{busy ? "Saving…" : "Save"}</button>
        </div>
      </div>
      <div className="pgrid">
        <label>Nationality<input value={draft.nationality || ""} onChange={(e) => setDraft({ ...draft, nationality: e.target.value || null })} placeholder="e.g. India" /></label>
        <label>Degree
          <select value={draft.degree || ""} onChange={(e) => setDraft({ ...draft, degree: e.target.value || null })}>
            <option value="">—</option>{DEGREE_OPTIONS.map((d) => <option key={d} value={d}>{degreeLabel(d)}</option>)}
          </select>
        </label>
        <label>Field
          <select value={draft.field || ""} onChange={(e) => setDraft({ ...draft, field: e.target.value || null })}>
            <option value="">—</option>{FIELD_OPTIONS.map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        </label>
        <label>GPA<input type="number" step="0.1" value={draft.gpa ?? ""} onChange={(e) => setDraft({ ...draft, gpa: num(e.target.value) })} placeholder="8.7" /></label>
        <label>GPA scale<input type="number" step="1" value={draft.gpa_scale ?? ""} onChange={(e) => setDraft({ ...draft, gpa_scale: num(e.target.value) })} placeholder="10" /></label>
        <label>IELTS<input type="number" step="0.5" value={draft.ielts ?? ""} onChange={(e) => setDraft({ ...draft, ielts: num(e.target.value) })} placeholder="7.5" /></label>
        <label>Grad year<input type="number" value={draft.graduation_year ?? ""} onChange={(e) => setDraft({ ...draft, graduation_year: num(e.target.value) })} placeholder="2025" /></label>
        <label>Experience (yrs)<input type="number" step="0.5" value={draft.experience_years ?? ""} onChange={(e) => setDraft({ ...draft, experience_years: num(e.target.value) })} placeholder="1" /></label>
      </div>
      {!profileIsEmpty(profile) && <button className="btn ghost sm" onClick={wipe} style={{ marginTop: 10 }}><Icon name="trash" size={12} /> Remove profile</button>}
    </div>
  );
}
