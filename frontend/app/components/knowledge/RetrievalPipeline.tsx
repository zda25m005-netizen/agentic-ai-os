"use client";
import Icon from "../Icon";
import { PIPELINE } from "../../lib/knowledgeApi";

export default function RetrievalPipeline() {
  return (
    <div className="pipeline">
      {PIPELINE.map((n, i) => (
        <span key={n.name} style={{ display: "flex", alignItems: "center" }}>
          <span className="pnode"><b>{n.name}</b><span>{n.desc}</span></span>
          {i < PIPELINE.length - 1 && <span className="parr"><Icon name="arrowRight" size={15} sw={2} /></span>}
        </span>
      ))}
    </div>
  );
}
