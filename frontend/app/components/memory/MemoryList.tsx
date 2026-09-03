"use client";
import Icon from "../Icon";
import { MemoryRecord, LAYERS, relativeTime } from "../../lib/memoryApi";

export const barLevel = (v: number) => (v >= 0.75 ? "hi" : v >= 0.45 ? "mid" : "lo");
const layerName = (id: string) => LAYERS.find((l) => l.id === id)?.name ?? id;

function Bar({ label, value }: { label: string; value: number }) {
  return (
    <div className="stat">
      <span className="k">{label}</span>
      <div className="barwrap">
        <div className={`bar ${barLevel(value)}`}><span style={{ width: `${Math.round(value * 100)}%` }} /></div>
        <span className="v">{Math.round(value * 100)}%</span>
      </div>
    </div>
  );
}

function MemoryItem({ rec, onOpen }: { rec: MemoryRecord; onOpen: (r: MemoryRecord) => void }) {
  return (
    <div className="item" onClick={() => onOpen(rec)}>
      <div className="item-top">
        <span className="tag-layer">{layerName(rec.layer)}</span>
        {rec.pinned && <span className="pin" title="Pinned"><Icon name="pin" size={13} sw={1.7} /></span>}
        <button className="dots" aria-label="Actions" onClick={(e) => { e.stopPropagation(); onOpen(rec); }}>
          <Icon name="more" size={16} />
        </button>
      </div>
      <div className="item-content">{rec.content}</div>
      <div className="stats">
        <Bar label="Importance" value={rec.importance} />
        <Bar label="Strength" value={rec.strength} />
        <div className="stat">
          <span className="k">Retrieved</span>
          <span className="v">{rec.retrievals} times</span>
        </div>
      </div>
      <div className="item-foot">
        <span className="src">{rec.source}</span>
        <span className="mid-dot">·</span>
        <span className="time">{relativeTime(rec.lastRetrieved)}</span>
        <div className="tags">{rec.tags.map((t) => <span className="tagchip" key={t}>{t}</span>)}</div>
      </div>
    </div>
  );
}

export default function MemoryList({ records, onOpen }: {
  records: MemoryRecord[]; onOpen: (r: MemoryRecord) => void;
}) {
  if (!records.length) {
    return (
      <div className="empty">
        <b>No memories yet</b>
        <span>Memories created by agents will appear here.</span>
      </div>
    );
  }
  return (
    <div className="list">
      {records.map((r) => <MemoryItem key={r.id} rec={r} onOpen={onOpen} />)}
    </div>
  );
}
