"use client";

import { useMemo } from "react";
import type { TaskOut, TaskStatus } from "../lib/api";

// Fill colors per task status (matches the badge palette in globals.css).
const FILL: Record<TaskStatus, string> = {
  pending: "#1a2438",
  ready: "#1c1808",
  running: "#0c1830",
  done: "#08160e",
  failed: "#170808",
  skipped: "#161c2b",
};
const STROKE: Record<TaskStatus, string> = {
  pending: "#33405e",
  ready: "#5c4d1e",
  running: "#24467e",
  done: "#1f7a44",
  failed: "#7a1f1f",
  skipped: "#33405e",
};

const NW = 190;
const NH = 56;
const COL = NW + 90;
const ROW = NH + 30;
const PAD = 24;

type Placed = TaskOut & { x: number; y: number };

// Lay the DAG out in columns by dependency depth (longest path from a root),
// stacking siblings vertically within each column.
function layout(tasks: TaskOut[]): { nodes: Placed[]; w: number; h: number } {
  const byId = new Map(tasks.map((t) => [t.id, t]));
  const depthCache = new Map<number, number>();

  function depth(id: number, seen: Set<number>): number {
    if (depthCache.has(id)) return depthCache.get(id)!;
    if (seen.has(id)) return 0; // guard against a cycle
    seen.add(id);
    const t = byId.get(id);
    const deps = (t?.depends_on || []).filter((d) => byId.has(d));
    const d = deps.length === 0 ? 0 : 1 + Math.max(...deps.map((x) => depth(x, seen)));
    depthCache.set(id, d);
    return d;
  }

  const rowByCol: Record<number, number> = {};
  const nodes: Placed[] = tasks.map((t) => {
    const col = depth(t.id, new Set());
    const row = rowByCol[col] ?? 0;
    rowByCol[col] = row + 1;
    return { ...t, x: PAD + col * COL, y: PAD + row * ROW };
  });

  const maxCol = Math.max(0, ...nodes.map((n) => (n.x - PAD) / COL));
  const maxRow = Math.max(1, ...Object.values(rowByCol));
  return {
    nodes,
    w: PAD * 2 + maxCol * COL + NW,
    h: PAD * 2 + maxRow * ROW,
  };
}

export default function TaskGraph({
  tasks,
  selected,
  onSelect,
}: {
  tasks: TaskOut[];
  selected?: number | null;
  onSelect?: (id: number) => void;
}) {
  const { nodes, w, h } = useMemo(() => layout(tasks), [tasks]);
  const pos = new Map(nodes.map((n) => [n.id, n]));

  if (tasks.length === 0) return <div className="empty">No tasks in this mission.</div>;

  return (
    <div className="graph-wrap">
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} role="img" aria-label="task graph">
        {/* edges: dependency -> dependent */}
        {nodes.flatMap((t) =>
          (t.depends_on || [])
            .filter((d) => pos.has(d))
            .map((d) => {
              const from = pos.get(d)!;
              const x1 = from.x + NW;
              const y1 = from.y + NH / 2;
              const x2 = t.x;
              const y2 = t.y + NH / 2;
              const mx = (x1 + x2) / 2;
              const eid = `te-${d}-${t.id}`;
              const live = t.status === "running"; // data flowing into a running task
              const dd = `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`;
              return (
                <g key={eid}>
                  <path id={eid} className={`graph-edge ${live ? "graph-edge-live" : ""}`} d={dd} />
                  {live && (
                    <circle r="4" className="graph-flow-dot">
                      <animateMotion dur="1s" repeatCount="indefinite">
                        <mpath href={`#${eid}`} />
                      </animateMotion>
                    </circle>
                  )}
                </g>
              );
            })
        )}
        {/* nodes */}
        {nodes.map((t) => {
          const isSel = selected === t.id;
          return (
            <g
              key={t.id}
              className={`graph-node gn-${t.status}`}
              transform={`translate(${t.x}, ${t.y})`}
              onClick={() => onSelect?.(t.id)}
              style={{ cursor: onSelect ? "pointer" : "default" }}
            >
              <rect
                width={NW}
                height={NH}
                rx={10}
                fill={FILL[t.status]}
                stroke={isSel ? "#4f8cff" : STROKE[t.status]}
                strokeWidth={isSel ? 2.5 : 1.5}
              />
              {t.status === "running" && <circle cx={NW - 13} cy={13} r={4} className="gn-dot" />}
              {t.status === "done" && <text x={NW - 18} y={17} className="gn-check">✓</text>}
              <text x={14} y={22}>
                {t.description.length > 26 ? t.description.slice(0, 25) + "…" : t.description}
              </text>
              <text className="node-sub" x={14} y={40}>
                #{t.id} · {t.status}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="legend">
        <span><i style={{ background: "#0c1830", border: "1px solid #24467e" }} /> running</span>
        <span><i style={{ background: "#08160e", border: "1px solid #1f7a44" }} /> done</span>
        <span><i style={{ background: "#1c1808", border: "1px solid #5c4d1e" }} /> ready</span>
        <span><i style={{ background: "#1a2438", border: "1px solid #33405e" }} /> pending</span>
        <span><i style={{ background: "#170808", border: "1px solid #7a1f1f" }} /> failed</span>
      </div>
    </div>
  );
}
