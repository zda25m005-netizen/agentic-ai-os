"use client";
import { STRATEGY } from "../../lib/knowledgeApi";

export default function RetrievalStrategy() {
  return (
    <div className="strat">
      {STRATEGY.map((s) => (
        <div className="strat-item" key={s.name}>
          <div className="sn">{s.name}</div>
          <div className="sp">{s.purpose}</div>
          <div className="st"><span className="d" /> Active</div>
        </div>
      ))}
    </div>
  );
}
