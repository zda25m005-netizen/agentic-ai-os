"use client";
import Icon from "../Icon";
import { LOOP } from "../../lib/agentsData";

export default function AgentLoop() {
  return (
    <div className="loop">
      {LOOP.map((n, i) => (
        <span key={n} style={{ display: "flex", alignItems: "center" }}>
          <span className="lnode">{n}</span>
          {i < LOOP.length - 1 && <span className="larr"><Icon name="arrowRight" size={15} sw={2} /></span>}
        </span>
      ))}
      <span className="lreplan">Critic rejection → bounded replan → Executor (max 3)</span>
    </div>
  );
}
