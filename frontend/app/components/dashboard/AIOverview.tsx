"use client";
import { OVERVIEW } from "../../lib/dashboardData";

// r chosen so the circumference ≈ 100, letting percentages map directly to dash length.
const R = 15.9155;

export default function AIOverview() {
  let acc = 0;
  return (
    <div className="panel">
      <div className="panel-head"><div className="panel-title">AI OS Overview</div></div>
      <div className="panel-sub">System overview</div>
      <div className="ov">
        <svg width="118" height="118" viewBox="0 0 42 42" role="img" aria-label="Usage breakdown">
          <circle cx="21" cy="21" r={R} fill="none" stroke="#20252A" strokeWidth="4" />
          {OVERVIEW.map((s, i) => {
            const seg = (
              <circle key={i} cx="21" cy="21" r={R} fill="none" stroke={s.color} strokeWidth="4"
                strokeDasharray={`${s.pct} ${100 - s.pct}`} strokeDashoffset={25 - acc} />
            );
            acc += s.pct;
            return seg;
          })}
        </svg>
        <div className="legend">
          {OVERVIEW.map((s) => (
            <div className="lg" key={s.label}>
              <i style={{ background: s.color }} />{s.label}
              <span className="lp">{s.pct}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
