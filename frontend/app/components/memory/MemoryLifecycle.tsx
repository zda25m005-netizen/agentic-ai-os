"use client";
import Icon from "../Icon";

const STEPS = ["Created", "Retrieved", "Reinforced", "Consolidated", "Long-term", "Decays if unused", "Pruned"];

export default function MemoryLifecycle() {
  return (
    <div className="panel">
      <div className="panel-title">Memory Lifecycle</div>
      <div className="life">
        {STEPS.map((s, i) => (
          <span key={s} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <span className={`step ${i >= 5 ? "dim" : ""}`}>{s}</span>
            {i < STEPS.length - 1 && <span className="arr"><Icon name="chevronRight" size={13} sw={2} /></span>}
          </span>
        ))}
      </div>
    </div>
  );
}
