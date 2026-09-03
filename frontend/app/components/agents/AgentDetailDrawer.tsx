"use client";
import Link from "next/link";
import Icon from "../Icon";
import { AgentView, STATUS_LABEL } from "../../lib/agentsData";

export default function AgentDetailDrawer({ agent, onClose }: { agent: AgentView; onClose: () => void }) {
  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label={`${agent.name} details`}>
        <div className="dh">
          <div>
            <div className="d-eyebrow">Agent · {agent.role}</div>
            <div className="d-name">{agent.name}</div>
          </div>
          <button className="dclose" onClick={onClose} aria-label="Close"><Icon name="x" size={16} /></button>
        </div>

        <div className="sec">
          <div className="sec-lbl">Description</div>
          <p>{agent.description}</p>
        </div>

        <div className="sec">
          <div className="sec-lbl">Status</div>
          <span className={`status ${agent.status}`}><span className="d" />{STATUS_LABEL[agent.status]}</span>
        </div>

        <div className="sec">
          <div className="sec-lbl">Loop position</div>
          <p style={{ fontSize: 12.5 }}>{agent.loopStage} — in the Planner → Executor → Critic → Finalize loop.</p>
        </div>

        <div className="sec">
          <div className="sec-lbl">Allowed tools</div>
          {agent.tools.length
            ? <div className="pills">{agent.tools.map((t) => <Link key={t} href="/tools" className="pill">{t}</Link>)}</div>
            : <p style={{ fontSize: 12.5, color: "var(--hmuted)" }}>No tools — evaluates outputs only.</p>}
        </div>

        <div className="sec">
          <div className="sec-lbl">Responsibilities</div>
          <ul className="resp">{agent.responsibilities.map((r) => <li key={r}>{r}</li>)}</ul>
        </div>

        <div className="sec">
          <div className="sec-lbl">Performance</div>
          <div className="note">
            Per-agent telemetry (success rate, latency, cost) isn’t exposed as an API yet.
            Aggregate runtime metrics are on <Link href="/observability">Observability</Link>.
          </div>
        </div>
      </aside>
    </>
  );
}
