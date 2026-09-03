"use client";

import { useEffect, useMemo, useState } from "react";
import "../memory.css";
import Icon from "../components/Icon";
import MemoryMetrics from "../components/memory/MemoryMetrics";
import MemoryLayers from "../components/memory/MemoryLayers";
import MemoryList from "../components/memory/MemoryList";
import MemoryDetailDrawer from "../components/memory/MemoryDetailDrawer";
import RecentConsolidations from "../components/memory/RecentConsolidations";
import ConflictIndicator from "../components/memory/ConflictIndicator";
import MemoryLifecycle from "../components/memory/MemoryLifecycle";
import {
  MemoryRecord, Layer, Consolidation, Conflict, LAYERS,
  fetchMemory, metrics, layerCounts, updateMemory, forgetMemory, togglePin, addMemory,
} from "../lib/memoryApi";

type Quick = "" | "importance" | "recent" | "frequent" | "decaying" | "pinned";
const QUICK: { id: Quick; label: string }[] = [
  { id: "importance", label: "Importance" },
  { id: "recent", label: "Recent" },
  { id: "frequent", label: "Frequently Retrieved" },
  { id: "decaying", label: "Decaying" },
  { id: "pinned", label: "Pinned" },
];

export default function MemoryPage() {
  const [records, setRecords] = useState<MemoryRecord[]>([]);
  const [consolidations, setConsolidations] = useState<Consolidation[]>([]);
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [query, setQuery] = useState("");
  const [layer, setLayer] = useState<Layer | "all">("all");
  const [quick, setQuick] = useState<Quick>("");
  const [openId, setOpenId] = useState<string | null>(null);
  const [openMode, setOpenMode] = useState<"view" | "edit">("view");

  useEffect(() => {
    fetchMemory().then((s) => {
      setRecords(s.records); setConsolidations(s.consolidations); setConflicts(s.conflicts);
    });
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    let out = records.filter((m) => {
      if (layer !== "all" && m.layer !== layer) return false;
      if (quick === "pinned" && !m.pinned) return false;
      if (quick === "decaying" && m.strength >= 0.4) return false;
      if (!q) return true;
      const hay = [m.content, m.source, m.mission?.title, m.layer, ...m.tags].join(" ").toLowerCase();
      return hay.includes(q);
    });
    if (quick === "importance") out = [...out].sort((a, b) => b.importance - a.importance);
    else if (quick === "frequent") out = [...out].sort((a, b) => b.retrievals - a.retrievals);
    else if (quick === "recent") out = [...out].sort((a, b) => +new Date(b.createdAt) - +new Date(a.createdAt));
    else if (quick === "decaying") out = [...out].sort((a, b) => a.strength - b.strength);
    return out;
  }, [records, query, layer, quick]);

  const open = records.find((m) => m.id === openId) || null;
  const m = metrics(records);
  const counts = layerCounts(records);

  const onUpdate = (id: string, patch: Partial<MemoryRecord>) => setRecords(updateMemory(id, patch));
  const onForget = (id: string) => { setRecords(forgetMemory(id)); setOpenId(null); };
  const onTogglePin = (id: string) => setRecords(togglePin(id));
  const onAdd = () => { const { records: r, id } = addMemory(); setRecords(r); setOpenMode("edit"); setOpenId(id); };
  const openRec = (r: MemoryRecord) => { setOpenMode("view"); setOpenId(r.id); };

  return (
    <div className="mem">
      <div className="wrap">
        <div className="head">
          <div>
            <h1 className="h1">Memory</h1>
            <p className="h-sub">Personal and agent memory across missions.</p>
          </div>
          <div className="head-actions">
            <div className="search">
              <Icon name="search" size={15} />
              <input placeholder="Search memories..." value={query} onChange={(e) => setQuery(e.target.value)} />
            </div>
            <button className="btn" onClick={onAdd}><Icon name="plus" size={14} sw={2} /> Add Memory</button>
          </div>
        </div>

        <MemoryMetrics m={m} />
        <MemoryLayers counts={counts} active={layer} onSelect={(l) => setLayer((cur) => (cur === l ? "all" : l))} />
        <ConflictIndicator conflicts={conflicts} onReview={() => setOpenId(conflicts[0]?.memoryIds[0] ?? null)} />

        <div className="filters">
          <button className={`chip ${layer === "all" ? "active" : ""}`} onClick={() => setLayer("all")}>All</button>
          {LAYERS.map((l) => (
            <button key={l.id} className={`chip ${layer === l.id ? "active" : ""}`} onClick={() => setLayer(l.id)}>{l.name}</button>
          ))}
          {QUICK.map((qf, i) => (
            <button key={qf.id} className={`chip ${i === 0 ? "sep" : ""} ${quick === qf.id ? "active" : ""}`}
              onClick={() => setQuick((c) => (c === qf.id ? "" : qf.id))}>{qf.label}</button>
          ))}
        </div>

        <MemoryList records={filtered} onOpen={openRec} />

        <div className="lower">
          <RecentConsolidations items={consolidations} />
          <MemoryLifecycle />
        </div>
      </div>

      {open && (
        <MemoryDetailDrawer
          rec={open} initialMode={openMode}
          onClose={() => setOpenId(null)}
          onUpdate={onUpdate} onForget={onForget} onTogglePin={onTogglePin}
        />
      )}
    </div>
  );
}
