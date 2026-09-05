"use client";
import Icon from "../Icon";
import { Scholarship, degreeLabel, eligibilityLabel, fundingLabel } from "../../lib/scholarshipsApi";

export default function ScholarshipCard({ s, saved, onOpen, onSave }: {
  s: Scholarship; saved: boolean; onOpen: (s: Scholarship) => void; onSave: (s: Scholarship) => void;
}) {
  const elig = eligibilityLabel(s.eligibility_status);
  const meta = [
    s.degree_levels.map(degreeLabel).join(" / "),
    s.scholarship_type ? s.scholarship_type[0].toUpperCase() + s.scholarship_type.slice(1) : null,
  ].filter(Boolean) as string[];
  return (
    <div className="scard" onClick={() => onOpen(s)}>
      <div className="sc-top">
        <span className="sc-title">{s.title}</span>
        {s.match_score != null && <span className="sc-match">{Math.round(s.match_score * 100)}% match</span>}
      </div>
      <div className="sc-org">{s.provider}{s.country ? ` · ${s.country}` : ""}</div>
      <div className="sc-badges">
        <span className={`fund ${s.funding_type}`}>{fundingLabel(s.funding_type)}</span>
        <span className={`elig ${elig.kind}`}>{elig.text}</span>
        {meta.map((m) => <span className="mtag" key={m}>{m}</span>)}
      </div>
      {s.match_reason && <div className="sc-reason">{s.match_reason}</div>}
      <div className="sc-sub">
        <span>Stipend: {s.stipend ?? "Not specified"}</span>
        <span className="dot">·</span>
        <span>Deadline: {s.deadline ?? (s.deadline_note ? "Annual — verify" : "Not specified")}</span>
        <span className="dot">·</span>
        <span>{s.intake.includes("annual") ? "Annual intake" : s.intake.join(", ")}</span>
      </div>
      <div className="sc-foot">
        <span className="sc-src">
          {s.is_verified ? "Verified" : "Curated · verify official"} · {s.sources.join(" · ")}
        </span>
        <button className={`btn ghost sm ${saved ? "saved" : ""}`}
          onClick={(e) => { e.stopPropagation(); onSave(s); }}>
          <Icon name={saved ? "bookmarkOn" : "bookmark"} size={13} /> {saved ? "Saved" : "Save"}
        </button>
        <a className="btn primary sm" href={s.application_url} target="_blank" rel="noreferrer noopener"
          title={s.apply_direct ? "Opens the official provider page" : `Opens ${s.source}`}
          onClick={(e) => e.stopPropagation()}>
          {s.apply_direct ? "Apply" : `View on ${s.source}`} <Icon name="arrowRight" size={13} sw={2} />
        </a>
      </div>
    </div>
  );
}
