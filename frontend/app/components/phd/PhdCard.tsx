"use client";
import Icon from "../Icon";
import { PhdOpportunity, eligibilityLabel, fundingLabel, oppLabel, deadlineLabel } from "../../lib/phdApi";

export default function PhdCard({ o, saved, onOpen, onSave }: {
  o: PhdOpportunity; saved: boolean; onOpen: (o: PhdOpportunity) => void; onSave: (o: PhdOpportunity) => void;
}) {
  const elig = eligibilityLabel(o.eligibility_status);
  return (
    <div className="scard" onClick={() => onOpen(o)}>
      <div className="sc-top">
        <span className="sc-title">{o.title}</span>
        {o.match_score != null && <span className="sc-match">{Math.round(o.match_score * 100)}% match</span>}
      </div>
      <div className="sc-org">{o.institution}{o.country ? ` · ${o.country}` : ""}{o.city ? `, ${o.city}` : ""}</div>
      <div className="sc-badges">
        <span className="mtag">{oppLabel(o.opportunity_type)}</span>
        <span className={`fund ${o.funding_type === "fully_funded" || o.funding_type === "salaried" ? "fully_funded" : ""}`}>{fundingLabel(o.funding_type)}</span>
        <span className={`elig ${elig.kind}`}>{elig.text}</span>
      </div>
      {o.match_reason && <div className="sc-reason">{o.match_reason}</div>}
      <div className="sc-sub">
        <span>Supervisor: {o.supervisor ?? "Not specified"}</span>
        <span className="dot">·</span>
        <span>{deadlineLabel(o)}</span>
      </div>
      <div className="sc-foot">
        <span className="sc-src">{o.is_verified ? "Verified" : "Curated · verify official"} · {o.sources.join(" · ")}</span>
        <button className={`btn ghost sm ${saved ? "saved" : ""}`} onClick={(e) => { e.stopPropagation(); onSave(o); }}>
          <Icon name={saved ? "bookmarkOn" : "bookmark"} size={13} /> {saved ? "Saved" : "Save"}
        </button>
        <a className="btn primary sm" href={o.official_application_url} target="_blank" rel="noreferrer noopener"
          onClick={(e) => e.stopPropagation()} title={o.apply_direct ? "Official page" : `Opens ${o.source}`}>
          {o.apply_direct ? "Official Application" : `View on ${o.source}`} <Icon name="arrowRight" size={13} sw={2} />
        </a>
      </div>
    </div>
  );
}
