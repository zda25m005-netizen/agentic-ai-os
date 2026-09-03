"use client";
import Icon from "../Icon";
import { EXAMPLES } from "../../lib/jobSearch";

const QUICK = ["ML Engineer", "Data Scientist", "Switzerland", "Germany", "0–2 years", "Remote"];

export default function JobSearchInput({ value, onChange, onSearch, searching, compact }: {
  value: string;
  onChange: (v: string) => void;
  onSearch: () => void;
  searching: boolean;
  compact?: boolean;
}) {
  const appendChip = (c: string) => {
    if (value.toLowerCase().includes(c.toLowerCase())) return;
    onChange((value.trim() + " " + c).trim());
  };
  return (
    <>
      {!compact && <div className="qlabel">What are you looking for?</div>}
      <div className="box">
        <textarea
          placeholder="Find ML Engineer and Data Scientist roles in Switzerland and Germany for 0–2 years experience. Prefer companies hiring fresh graduates and show salary when available."
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) onSearch(); }}
        />
        <div className="chips">
          {QUICK.map((c) => (
            <button key={c} className={`chip ${value.toLowerCase().includes(c.toLowerCase()) ? "active" : ""}`}
              onClick={() => appendChip(c)}>{c}</button>
          ))}
        </div>
        <div className="box-foot">
          {!compact && (
            <div className="examples">
              <span style={{ fontSize: 11, color: "var(--hmeta)", alignSelf: "center" }}>Try:</span>
              {EXAMPLES.map((ex) => (
                <button key={ex} className="ex" onClick={() => onChange(ex)}>{ex}</button>
              ))}
            </div>
          )}
          {compact && <span style={{ flex: 1 }} />}
          <button className="btn primary" onClick={onSearch} disabled={!value.trim() || searching}>
            {searching ? "Searching…" : <>Search Jobs <Icon name="arrowRight" size={14} sw={2} /></>}
          </button>
        </div>
      </div>
    </>
  );
}
