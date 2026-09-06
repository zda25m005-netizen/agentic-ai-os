"use client";
import Icon from "../Icon";
import { PhdOpportunity, eligibilityLabel, fundingLabel, oppLabel, deadlineLabel, setTrackingStatus } from "../../lib/phdApi";
import { checkMark } from "../../lib/scholarshipsApi";

const LABELS: Record<string, string> = {
  research: "Research fit", country: "Country", funding: "Funding", eligibility: "Eligibility", profile: "Profile fit", timing: "Timing",
};
const TRACK = ["Interested", "Preparing", "Applied", "Interview", "Accepted", "Rejected"];

export default function PhdDrawer({ o, saved, onClose, onSave, onWriteSop }: {
  o: PhdOpportunity; saved: boolean; onClose: () => void; onSave: (o: PhdOpportunity) => void; onWriteSop: (o: PhdOpportunity) => void;
}) {
  const elig = eligibilityLabel(o.eligibility_status);
  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label={o.title}>
        <div className="dhead">
          <div>
            <div className="dkicker">{oppLabel(o.opportunity_type)}</div>
            <div className="dtitle">{o.title}</div>
            <div className="dco">{o.institution}{o.department ? ` · ${o.department}` : ""} · {o.country}</div>
          </div>
          <button className="head-link" onClick={onClose} aria-label="Close"><Icon name="x" size={16} /></button>
        </div>

        <div className="sc-badges" style={{ marginBottom: 14 }}>
          <span className="fund fully_funded">{fundingLabel(o.funding_type)}</span>
          <span className={`elig ${elig.kind}`}>{elig.text}</span>
        </div>

        {o.match_score != null && (
          <div className="matchbox">
            <div className="mb-head"><span>Why this matches you</span><b>{Math.round(o.match_score * 100)}%</b></div>
            {Object.entries(o.match_breakdown).map(([k, v]) => (
              <div className="mb-row" key={k}>
                <span className="mb-k">{LABELS[k] || k}</span>
                <span className="mb-bar"><span style={{ width: `${Math.round(v * 100)}%` }} /></span>
                <span className="mb-v">{Math.round(v * 100)}%</span>
              </div>
            ))}
            {o.match_reason && <div className="mb-note" style={{ marginTop: 8 }}>{o.match_reason}</div>}
          </div>
        )}

        <div className="sec-h" style={{ margin: "16px 0 8px" }}>Eligibility</div>
        <div className="checks">
          {o.eligibility_checks.filter((c) => c.status !== "NOT_APPLICABLE").map((c, i) => {
            const m = checkMark(c.status);
            return (
              <div className="chk" key={i}>
                <span className={`chk-m ${m.kind}`}>{m.sym}</span>
                <span className="chk-body"><b>{c.requirement}</b>{c.required_value ? <span className="chk-req"> · needs {c.required_value}</span> : null}{c.user_value ? <span className="chk-you"> · you: {c.user_value}</span> : null}{c.explanation ? <div className="chk-exp">{c.explanation}</div> : null}</span>
              </div>
            );
          })}
        </div>

        <div className="sec-h" style={{ margin: "16px 0 8px" }}>Application checklist</div>
        <div className="checks">
          {o.application_checklist.map((it, i) => (
            <div className="chk" key={i}>
              <span className={`chk-m ${it.kind === "required" ? "unclear" : it.kind === "note" ? "na" : "ok"}`}>{it.kind === "note" ? "•" : it.kind === "required" ? "!" : "•"}</span>
              <span className="chk-body">{it.item}{it.kind === "typical" ? <span className="chk-req"> · typical</span> : it.kind === "required" ? <span className="chk-req"> · required</span> : null}</span>
            </div>
          ))}
        </div>

        <div className="crow" style={{ margin: "16px 0" }}>
          <span className="k">Funding</span><span className="v">{fundingLabel(o.funding_type)}{o.stipend ? ` · ${o.stipend}` : ""}</span>
          <span className="k">Supervisor</span><span className="v">{o.supervisor ?? "Not specified"}</span>
          <span className="k">Research group</span><span className="v">{o.research_group ?? "Not specified"}</span>
          <span className="k">Deadline</span><span className="v">{deadlineLabel(o)}</span>
          <span className="k">Language</span><span className="v">{o.language_requirements ?? "Not specified"}</span>
          <span className="k">Source</span><span className="v">{o.sources.join(" · ")}</span>
        </div>

        {o.description && <p style={{ fontSize: 13, lineHeight: 1.55, color: "var(--htext)" }}>{o.description}</p>}

        {saved && (
          <div style={{ margin: "12px 0" }}>
            <div className="sec-h" style={{ margin: "0 0 8px" }}>Track application</div>
            <select className="tb-sort" defaultValue={o.tracking_status || "Interested"} onChange={(e) => setTrackingStatus(o.id, e.target.value)}>
              {TRACK.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
        )}

        <div className="dnote">Verify all details on the official source before applying.</div>
        <div className="dactions">
          <button className={`btn ghost ${saved ? "saved" : ""}`} onClick={() => onSave(o)}>
            <Icon name={saved ? "bookmarkOn" : "bookmark"} size={14} /> {saved ? "Saved" : "Save"}
          </button>
          <button className="btn ghost" onClick={() => onWriteSop(o)}><Icon name="file" size={14} /> Write SOP</button>
          <a className="btn primary" href={o.official_application_url} target="_blank" rel="noreferrer noopener">
            {o.apply_direct ? "Official Application" : `View on ${o.source}`} <Icon name="external" size={13} />
          </a>
        </div>
      </aside>
    </>
  );
}
