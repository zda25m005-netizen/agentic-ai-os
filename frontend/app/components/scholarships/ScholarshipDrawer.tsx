"use client";
import Icon from "../Icon";
import {
  Scholarship, degreeLabel, eligibilityLabel, fundingLabel, setTrackingStatus, checkMark, opportunityLabel,
} from "../../lib/scholarshipsApi";

const LABELS: Record<string, string> = {
  field: "Study field", country: "Country", degree: "Degree level", funding: "Funding",
  eligibility: "Eligibility", intake: "Intake", profile: "Profile fit",
};
const TRACK = ["Interested", "Preparing", "Applied", "Interview/Selection", "Awarded", "Rejected"];

export default function ScholarshipDrawer({ s, saved, onClose, onSave }: {
  s: Scholarship; saved: boolean; onClose: () => void; onSave: (s: Scholarship) => void;
}) {
  const elig = eligibilityLabel(s.eligibility_status);
  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label={s.title}>
        <div className="dhead">
          <div>
            <div className="dkicker">Scholarship</div>
            <div className="dtitle">{s.title}</div>
            <div className="dco">{s.provider}{s.institution ? ` · ${s.institution}` : ""} · {s.country}</div>
          </div>
          <button className="head-link" onClick={onClose} aria-label="Close"><Icon name="x" size={16} /></button>
        </div>

        <div className="sc-badges" style={{ marginBottom: 14 }}>
          <span className={`fund ${s.funding_type}`}>{fundingLabel(s.funding_type)}</span>
          <span className={`elig ${elig.kind}`}>{elig.text}</span>
          {s.opportunity_type !== "scholarship" && <span className="mtag">{opportunityLabel(s.opportunity_type)}</span>}
          {s.degree_levels.map((d) => <span className="mtag" key={d}>{degreeLabel(d)}</span>)}
        </div>

        {s.match_score != null && (
          <div className="matchbox">
            <div className="mb-head"><span>Why this matches you</span><b>{Math.round(s.match_score * 100)}%</b></div>
            {Object.entries(s.match_breakdown).map(([k, v]) => (
              <div className="mb-row" key={k}>
                <span className="mb-k">{LABELS[k] || k}</span>
                <span className="mb-bar"><span style={{ width: `${Math.round(v * 100)}%` }} /></span>
                <span className="mb-v">{Math.round(v * 100)}%</span>
              </div>
            ))}
            {s.match_reason && <div className="mb-note" style={{ marginTop: 8 }}>{s.match_reason}</div>}
          </div>
        )}

        <div className="sec-h" style={{ margin: "16px 0 8px" }}>Why this matches you</div>
        <div className="checks">
          {s.eligibility_checks.filter((c) => c.status !== "NOT_APPLICABLE").map((c, idx) => {
            const m = checkMark(c.status);
            return (
              <div className="chk" key={idx}>
                <span className={`chk-m ${m.kind}`}>{m.sym}</span>
                <span className="chk-body">
                  <b>{c.requirement}</b>
                  {c.required_value ? <span className="chk-req"> · needs {c.required_value}</span> : null}
                  {c.user_value ? <span className="chk-you"> · you: {c.user_value}</span> : null}
                  {c.explanation ? <div className="chk-exp">{c.explanation}</div> : null}
                </span>
              </div>
            );
          })}
          {s.eligibility_checks.every((c) => c.status === "NOT_APPLICABLE") && (
            <div className="chk-exp">No structured requirements published — verify on the official page.</div>
          )}
        </div>

        <div className="crow" style={{ margin: "16px 0" }}>
          <span className="k">Funding</span><span className="v">{fundingLabel(s.funding_type)}</span>
          <span className="k">Stipend</span><span className="v">{s.stipend ?? "Not specified"}</span>
          <span className="k">Deadline</span><span className="v">{s.deadline ?? (s.deadline_note ?? "Not specified")}</span>
          <span className="k">Intake</span><span className="v">{s.intake.join(", ")}</span>
          <span className="k">Language</span><span className="v">{s.language_requirements ?? "Not specified"}</span>
          <span className="k">Source</span><span className="v">{s.sources.join(" · ")}</span>
        </div>

        {s.description && (
          <div style={{ marginBottom: 8 }}>
            <div className="sec-h" style={{ margin: "0 0 8px" }}>Overview</div>
            <p style={{ fontSize: 13, lineHeight: 1.55, color: "var(--htext)" }}>{s.description}</p>
          </div>
        )}

        {saved && (
          <div style={{ margin: "12px 0" }}>
            <div className="sec-h" style={{ margin: "0 0 8px" }}>Track application</div>
            <select className="tb-sort" defaultValue={s.tracking_status || "Interested"}
              onChange={(e) => setTrackingStatus(s.id, e.target.value)}>
              {TRACK.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
        )}

        <div className="dnote">Verify all details on the official source before applying.</div>
        <div className="dactions">
          <button className={`btn ghost ${saved ? "saved" : ""}`} onClick={() => onSave(s)}>
            <Icon name={saved ? "bookmarkOn" : "bookmark"} size={14} /> {saved ? "Saved" : "Save scholarship"}
          </button>
          <a className="btn primary" href={s.application_url} target="_blank" rel="noreferrer noopener">
            {s.apply_direct ? "Open official page" : `View on ${s.source}`} <Icon name="external" size={13} />
          </a>
        </div>
      </aside>
    </>
  );
}
