"use client";
import { useRef, useState } from "react";
import Icon from "../Icon";
import { ResumeState, uploadResume, removeResume, experienceLabel } from "../../lib/resumeApi";

const STEPS = ["Uploading resume", "Extracting text", "Analyzing with AI", "Building profile", "Ready"];

export default function ResumePanel({ state, onChange, onView }: {
  state: ResumeState | null;
  onChange: (s: ResumeState | null) => void;
  onView: () => void;
}) {
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const pick = () => fileRef.current?.click();

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setBusy(true); setError(null); setStep(0);
    timer.current = setInterval(() => setStep((s) => Math.min(s + 1, 3)), 700);
    try {
      const s = await uploadResume(file);
      if (timer.current) clearInterval(timer.current);
      setStep(4);
      onChange(s);
    } catch (err) {
      if (timer.current) clearInterval(timer.current);
      setError(err instanceof Error ? err.message : "Unable to analyze this resume.");
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => { await removeResume(); onChange({ exists: false }); };

  const profile = state?.profile;

  return (
    <div className="resume">
      <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" onChange={onFile} style={{ display: "none" }} />
      <div className="resume-head">
        <span className="sec-h" style={{ margin: 0 }}>Your profile</span>
        {state?.exists && !busy && (
          <div className="resume-actions">
            <button className="btn ghost sm" onClick={onView}>View profile</button>
            <button className="btn ghost sm" onClick={pick}>Replace</button>
            <button className="btn ghost sm" onClick={remove}><Icon name="trash" size={13} /> Remove</button>
          </div>
        )}
      </div>

      {busy ? (
        <div className="resume-progress">
          <span className="spin" />
          <span>{STEPS[step]}…</span>
        </div>
      ) : error ? (
        <div className="resume-empty">
          <div className="resume-err">{error}</div>
          <button className="btn ghost sm" onClick={pick}>Try again</button>
        </div>
      ) : state?.exists && profile ? (
        <div className="resume-summary">
          <div className="rs-row">
            <Icon name="check" size={15} style={{ color: "var(--hgreen)" }} />
            <span className="rs-ok">Resume analyzed</span>
            <span className="rs-file">{state.filename}</span>
          </div>
          {profile.skills.length > 0 && (
            <div className="rs-skills">
              {profile.skills.slice(0, 8).map((s) => <span className="tagv" key={s}>{s}</span>)}
              {profile.skills.length > 8 && <span className="rs-more">+{profile.skills.length - 8}</span>}
            </div>
          )}
          <div className="rs-meta">
            Experience: {experienceLabel(profile.experience_years)}
            {state.suggested_roles && state.suggested_roles.length > 0 &&
              <> · Suggested: {state.suggested_roles.slice(0, 3).join(" · ")}</>}
          </div>
          {state.sparse && (
            <div className="rs-warn">Resume analyzed, but limited profile information was found.</div>
          )}
        </div>
      ) : (
        <div className="resume-empty">
          <div>
            <div className="resume-cta-title">Upload your resume to get personalized job recommendations.</div>
            <div className="resume-consent">PDF, DOCX or TXT. Your resume text is sent to the configured AI model
              for analysis; only the extracted profile is stored — never the file itself.</div>
          </div>
          <button className="btn primary sm" onClick={pick}><Icon name="file" size={14} /> Upload Resume</button>
        </div>
      )}
    </div>
  );
}
