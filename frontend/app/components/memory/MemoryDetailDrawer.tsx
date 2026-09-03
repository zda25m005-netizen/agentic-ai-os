"use client";
import { useState } from "react";
import Link from "next/link";
import Icon from "../Icon";
import { MemoryRecord, Layer, LAYERS, shortDate, relativeTime } from "../../lib/memoryApi";

type Mode = "view" | "edit" | "forget";

export default function MemoryDetailDrawer({ rec, onClose, onUpdate, onForget, onTogglePin, initialMode = "view" }: {
  rec: MemoryRecord;
  onClose: () => void;
  onUpdate: (id: string, patch: Partial<MemoryRecord>) => void;
  onForget: (id: string) => void;
  onTogglePin: (id: string) => void;
  initialMode?: Mode;
}) {
  const [mode, setMode] = useState<Mode>(initialMode);
  const [content, setContent] = useState(rec.content);
  const [layer, setLayer] = useState<Layer>(rec.layer);
  const [importance, setImportance] = useState(Math.round(rec.importance * 100));
  const [tags, setTags] = useState(rec.tags.join(", "));

  const save = () => {
    onUpdate(rec.id, {
      content: content.trim() || rec.content,
      layer,
      importance: Math.min(1, Math.max(0, importance / 100)),
      tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
    });
    setMode("view");
  };

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label="Memory detail">
        <div className="drawer-head">
          <span className="drawer-eyebrow">Memory · {LAYERS.find((l) => l.id === rec.layer)?.name}</span>
          <button className="dots" onClick={onClose} aria-label="Close"><Icon name="x" size={16} /></button>
        </div>

        {mode === "view" && (
          <>
            <div className="drawer-content">{rec.content}</div>
            <div className="kv">
              <span className="k">Importance</span><span className="v">{Math.round(rec.importance * 100)}%</span>
              <span className="k">Strength</span><span className="v">{Math.round(rec.strength * 100)}%</span>
              <span className="k">Created</span><span className="v">{shortDate(rec.createdAt)}</span>
              <span className="k">Last retrieved</span><span className="v">{relativeTime(rec.lastRetrieved)}</span>
              <span className="k">Retrieved</span><span className="v">{rec.retrievals} times</span>
              <span className="k">Source</span><span className="v">{rec.source}</span>
              {rec.mission && (
                <>
                  <span className="k">Mission</span>
                  <span className="v"><Link href={`/missions/${rec.mission.id}`}>{rec.mission.title}</Link></span>
                </>
              )}
              <span className="k">Status</span>
              <span className="v">{rec.pinned ? "Pinned — protected from decay" : "Active"}</span>
            </div>
            <div className="drawer-tags">{rec.tags.map((t) => <span className="tagchip" key={t}>{t}</span>)}</div>
            <div className="drawer-actions">
              <button className="btn ghost" onClick={() => setMode("edit")}><Icon name="edit" size={14} /> Edit</button>
              <button className="btn ghost" onClick={() => onTogglePin(rec.id)}>
                <Icon name="pin" size={14} /> {rec.pinned ? "Unpin" : "Pin"}
              </button>
              <button className="btn danger" onClick={() => setMode("forget")}><Icon name="trash" size={14} /> Forget</button>
            </div>
          </>
        )}

        {mode === "edit" && (
          <>
            <div className="field">
              <label>Memory content</label>
              <textarea value={content} onChange={(e) => setContent(e.target.value)} />
            </div>
            <div className="field">
              <label>Layer</label>
              <select value={layer} onChange={(e) => setLayer(e.target.value as Layer)}>
                {LAYERS.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            </div>
            <div className="field">
              <label>Importance — {importance}%</label>
              <input type="range" min={0} max={100} value={importance}
                onChange={(e) => setImportance(Number(e.target.value))} />
            </div>
            <div className="field">
              <label>Tags (comma separated)</label>
              <input value={tags} onChange={(e) => setTags(e.target.value)} />
            </div>
            <div className="drawer-actions">
              <button className="btn ghost" onClick={() => setMode("view")}>Cancel</button>
              <button className="btn" onClick={save}>Save Changes</button>
            </div>
          </>
        )}

        {mode === "forget" && (
          <>
            <div className="confirm">
              <b>Forget this memory?</b>
              <p>This memory will no longer be available to agents.</p>
            </div>
            <div className="drawer-actions">
              <button className="btn ghost" onClick={() => setMode("view")}>Cancel</button>
              <button className="btn danger" onClick={() => onForget(rec.id)}>
                <Icon name="trash" size={14} /> Forget Memory
              </button>
            </div>
          </>
        )}
      </aside>
    </>
  );
}
