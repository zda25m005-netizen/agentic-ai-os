"use client";
import Icon from "../Icon";

// High-level operational status only — never chain-of-thought or raw queries.
const STEPS = [
  "Understanding search criteria",
  "Searching available sources",
  "Collecting listings",
  "Removing duplicates",
  "Ranking opportunities",
];

export default function SearchProgress({ step }: { step: number }) {
  return (
    <div className="progress">
      <div className="sec-h" style={{ margin: "0 0 12px" }}>Searching</div>
      {STEPS.map((label, i) => {
        const state = i < step ? "done" : i === step ? "active" : "pending";
        return (
          <div className={`pstep ${state}`} key={label}>
            <span className="pdot">
              {state === "done" ? <Icon name="check" size={14} />
                : state === "active" ? <span className="spin" /> : <span className="idle" />}
            </span>
            <span className="plabel">{label}</span>
          </div>
        );
      })}
    </div>
  );
}
