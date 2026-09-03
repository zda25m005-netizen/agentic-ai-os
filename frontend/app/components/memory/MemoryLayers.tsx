"use client";
import { LAYERS, Layer } from "../../lib/memoryApi";

export default function MemoryLayers({ counts, active, onSelect }: {
  counts: Record<Layer, number>;
  active: Layer | "all";
  onSelect: (l: Layer) => void;
}) {
  return (
    <div className="layers">
      {LAYERS.map((l) => (
        <button key={l.id} className={`layer ${active === l.id ? "active" : ""}`} onClick={() => onSelect(l.id)}>
          <div className="lname">{l.name}</div>
          <div className="lcount">{counts[l.id]}<span>memories</span></div>
          <div className="ldesc">{l.desc}</div>
        </button>
      ))}
    </div>
  );
}
