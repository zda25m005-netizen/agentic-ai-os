"use client";
import Icon from "../Icon";
import { ToolView } from "../../lib/toolsApi";

function ToolCard({ t, onOpen }: { t: ToolView; onOpen: (t: ToolView) => void }) {
  return (
    <button className="card" onClick={() => onOpen(t)}>
      <div className="card-top">
        <span className="tool-ico"><Icon name={t.icon} size={17} sw={1.7} /></span>
        <span className="name-wrap">
          <div className="tool-name">{t.displayName}</div>
          <div className="tool-id">{t.id}</div>
        </span>
        <span className={`status ${t.status}`}><span className="d" />{t.status[0].toUpperCase() + t.status.slice(1)}</span>
      </div>
      <div className="tool-desc">{t.description}</div>
      <div className="badges">
        {t.safety.map((s) => <span className="badge" key={s}><Icon name="shield" size={11} sw={1.7} />{s}</span>)}
      </div>
      <div className="card-foot">
        <span>Used by {t.agents.length} agent{t.agents.length === 1 ? "" : "s"}</span>
        <span className="open">Open Tool <Icon name="arrowRight" size={13} sw={2} /></span>
      </div>
    </button>
  );
}

export default function ToolGrid({ groups, onOpen }: {
  groups: { title: string; tools: ToolView[] }[];
  onOpen: (t: ToolView) => void;
}) {
  const empty = groups.every((g) => g.tools.length === 0);
  if (empty) {
    return (
      <div className="empty">
        <b>No tools found</b>
        <span>Try a different search or category.</span>
      </div>
    );
  }
  return (
    <>
      {groups.filter((g) => g.tools.length).map((g) => (
        <div key={g.title}>
          {g.title && <div className="group-h">{g.title}</div>}
          <div className="grid">
            {g.tools.map((t) => <ToolCard key={t.id} t={t} onOpen={onOpen} />)}
          </div>
        </div>
      ))}
    </>
  );
}
