"use client";
import Icon from "../Icon";
import { AgentView, STATUS_LABEL } from "../../lib/agentsData";

function AgentCard({ a, onOpen }: { a: AgentView; onOpen: (a: AgentView) => void }) {
  return (
    <button className="card" onClick={() => onOpen(a)}>
      <div className="card-top">
        <span className="aname">{a.name}</span>
        <span className={`status ${a.status}`}><span className="d" />{STATUS_LABEL[a.status]}</span>
      </div>
      <div className="adesc">{a.description}</div>
      <div className="ameta">
        <div><div className="k">Role</div><div className="v">{a.role}</div></div>
        <div><div className="k">Tools</div><div className="v">{a.tools.length}</div></div>
        <div><div className="k">Loop</div><div className="v">{a.loopStage}</div></div>
        <span className="aopen">Open <Icon name="arrowRight" size={13} sw={2} /></span>
      </div>
    </button>
  );
}

export default function AgentGrid({ agents, onOpen }: { agents: AgentView[]; onOpen: (a: AgentView) => void }) {
  if (!agents.length) {
    return <div className="empty"><b>No agents found</b><span>Try a different search or role filter.</span></div>;
  }
  return <div className="grid">{agents.map((a) => <AgentCard key={a.id} a={a} onOpen={onOpen} />)}</div>;
}
