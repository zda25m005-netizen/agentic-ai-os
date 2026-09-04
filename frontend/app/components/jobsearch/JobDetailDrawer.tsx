"use client";
import Icon from "../Icon";
import { JobListing, postedLabel, salaryLabel } from "../../lib/jobSearch";

const LABELS: Record<string, string> = {
  role: "Role", skills: "Skills", experience: "Experience", location: "Location",
};

export default function JobDetailDrawer({ job, saved, onClose, onSave }: {
  job: JobListing; saved: boolean; onClose: () => void; onSave: (j: JobListing) => void;
}) {
  const sal = salaryLabel(job);
  const breakdown = Object.entries(job.matchBreakdown);
  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label={`${job.title} at ${job.company}`}>
        <div className="dhead">
          <div>
            <div className="dkicker">Job details</div>
            <div className="dtitle">{job.title}</div>
            <div className="dco">{job.company}{job.location ? ` · ${job.location}` : ""}</div>
          </div>
          <button className="head-link" onClick={onClose} aria-label="Close"><Icon name="x" size={16} /></button>
        </div>

        {job.candidateScore != null ? (
          <div className="matchbox">
            <div className="mb-head"><span>Candidate match</span><b>{Math.round(job.candidateScore * 100)}%</b></div>
            {Object.entries(job.candidateBreakdown).map(([k, v]) => (
              <div className="mb-row" key={k}>
                <span className="mb-k">{LABELS[k] || k}</span>
                <span className="mb-bar"><span style={{ width: `${Math.round(v * 100)}%` }} /></span>
                <span className="mb-v">{Math.round(v * 100)}%</span>
              </div>
            ))}
            {job.matchReason && <div className="mb-note" style={{ marginTop: 8 }}>{job.matchReason}</div>}
            {(job.matchedSkills.length > 0 || job.missingSkills.length > 0) && (
              <div className="gaps">
                {job.matchedSkills.length > 0 && (
                  <div><span className="gap-lbl">Strong match</span>
                    <span className="v" style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                      {job.matchedSkills.map((s) => <span className="tagv hit" key={s}>{s}</span>)}</span></div>
                )}
                {job.missingSkills.length > 0 && (
                  <div style={{ marginTop: 8 }}><span className="gap-lbl">Not demonstrated in resume</span>
                    <span className="v" style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                      {job.missingSkills.map((s) => <span className="tagv gap" key={s}>{s}</span>)}</span></div>
                )}
              </div>
            )}
          </div>
        ) : job.matchScore != null && (
          <div className="matchbox">
            <div className="mb-head"><span>Why it matches</span><b>{Math.round(job.matchScore * 100)}%</b></div>
            {breakdown.length > 0 ? breakdown.map(([k, v]) => (
              <div className="mb-row" key={k}>
                <span className="mb-k">{LABELS[k] || k}</span>
                <span className="mb-bar"><span style={{ width: `${Math.round(v * 100)}%` }} /></span>
                <span className="mb-v">{Math.round(v * 100)}%</span>
              </div>
            )) : <div className="mb-note">Neutral — no specific criteria were given to match against.</div>}
          </div>
        )}

        <div className="crow" style={{ margin: "16px 0" }}>
          <span className="k">Employment</span><span className="v">{job.employmentType ?? "—"}</span>
          <span className="k">Workplace</span><span className="v">{job.workplaceType ?? "—"}</span>
          <span className="k">Experience</span><span className="v">{job.experience ?? "—"}</span>
          <span className="k">Salary</span><span className="v"><span className={`sal ${sal.kind}`}>{sal.text}</span></span>
          <span className="k">Posted</span><span className="v">{postedLabel(job.postedAt)}</span>
          <span className="k">Source</span><span className="v">{job.sources.join(" · ")}</span>
        </div>

        {job.skills.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div className="sec-h" style={{ margin: "0 0 8px" }}>Key requirements</div>
            <div className="v" style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {job.skills.map((s) => <span className="tagv" key={s}>{s}</span>)}
            </div>
          </div>
        )}
        {job.description && (
          <div style={{ marginBottom: 8 }}>
            <div className="sec-h" style={{ margin: "0 0 8px" }}>Description</div>
            <p style={{ fontSize: 13, lineHeight: 1.55, color: "var(--htext)" }}>{job.description}</p>
          </div>
        )}

        <div className="dactions">
          <button className={`btn ghost ${saved ? "saved" : ""}`} onClick={() => onSave(job)}>
            <Icon name={saved ? "bookmarkOn" : "bookmark"} size={14} /> {saved ? "Saved" : "Save Job"}
          </button>
          <a className="btn primary" href={job.applicationUrl} target="_blank" rel="noreferrer noopener"
            title={job.applyDirect ? "Opens the employer/ATS application" : `Opens ${job.source} (aggregator)`}>
            {job.applyDirect ? "Apply on company site" : `Apply via ${job.source}`} <Icon name="external" size={13} />
          </a>
        </div>
      </aside>
    </>
  );
}
