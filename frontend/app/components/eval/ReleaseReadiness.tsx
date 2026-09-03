"use client";
import { BENCHMARK, status } from "../../lib/evalData";

export default function ReleaseReadiness() {
  const items = BENCHMARK.metrics.map((m) => ({ name: m.name, pass: status(m) === "passing" }));
  const ready = items.every((i) => i.pass);
  return (
    <div className="card">
      <div className="release">
        {items.map((i) => (
          <div className={`ritem ${i.pass ? "pass" : "review"}`} key={i.name}>
            {i.name}<span className="mark">{i.pass ? "✓ PASS" : "⚠ REVIEW"}</span>
          </div>
        ))}
      </div>
      <div className="release-overall">
        <b>Overall</b>
        <span className="verdict">{ready ? "READY" : "NOT READY"}</span>
      </div>
      <p className="release-note">Evaluation status only — reflects whether metrics meet their targets,
        not an automated deployment gate.</p>
    </div>
  );
}
