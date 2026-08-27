"use client";

import { EDGES, GraphNode, NODES, NodeState } from "../lib/demo";

const NW = 128;
const NH = 50;

const FILL: Record<NodeState, string> = {
  idle: "#111318",
  queued: "#131a24",
  running: "#0b1f2e",
  done: "#08160e",
  failed: "#1a0b0b",
  retry: "#1c1608",
};
const STROKE: Record<NodeState, string> = {
  idle: "#20242B",
  queued: "#33405e",
  running: "#22d3ee",
  done: "#1f7a44",
  failed: "#7a1f1f",
  retry: "#5c4d1e",
};

function node(id: string): GraphNode {
  return NODES.find((n) => n.id === id)!;
}

function edgePath(from: string, to: string): string {
  const a = node(from);
  const b = node(to);
  if (from === "critic" && to === "executor") {
    // retry: bow out to the right, travelling upward
    return `M ${a.x + NW / 2} ${a.y} C ${a.x + 170} ${a.y}, ${b.x + 170} ${b.y}, ${b.x + NW / 2} ${b.y}`;
  }
  const y1 = a.y + NH / 2;
  const y2 = b.y - NH / 2;
  const my = (y1 + y2) / 2;
  return `M ${a.x} ${y1} C ${a.x} ${my}, ${b.x} ${my}, ${b.x} ${y2}`;
}

export default function AgentGraph({
  states,
  activeEdge,
}: {
  states: Record<string, NodeState>;
  activeEdge?: [string, string];
}) {
  return (
    <svg viewBox="0 0 900 560" className="agent-graph" role="img" aria-label="agent execution graph">
      <defs>
        <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="#33405e" />
        </marker>
      </defs>

      {EDGES.map((e, i) => {
        const active = activeEdge && activeEdge[0] === e.from && activeEdge[1] === e.to;
        const id = `edge-${e.from}-${e.to}`;
        return (
          <g key={i}>
            <path
              id={id}
              d={edgePath(e.from, e.to)}
              className={`edge ${active ? "edge-active" : ""}`}
              markerEnd="url(#arrow)"
            />
            {active && (
              <circle r="4.5" className="flow-dot">
                <animateMotion dur="0.9s" repeatCount="indefinite">
                  <mpath href={`#${id}`} />
                </animateMotion>
              </circle>
            )}
          </g>
        );
      })}

      {NODES.map((n) => {
        const st = states[n.id] ?? "idle";
        return (
          <g key={n.id} transform={`translate(${n.x - NW / 2}, ${n.y - NH / 2})`} className={`gnode gnode-${st}`}>
            <rect width={NW} height={NH} rx={11} fill={FILL[st]} stroke={STROKE[st]} strokeWidth={st === "running" ? 2 : 1.4} />
            <text x={NW / 2} y={n.sub ? 22 : 30} textAnchor="middle" className="gnode-label">
              {n.label}
            </text>
            {n.sub && (
              <text x={NW / 2} y={37} textAnchor="middle" className="gnode-sub">
                {n.sub}
              </text>
            )}
            {st === "running" && <circle cx={NW - 14} cy={14} r={4} className="gnode-spin" />}
            {st === "done" && <text x={NW - 16} y={18} className="gnode-badge ok">✓</text>}
            {st === "failed" && <text x={NW - 16} y={18} className="gnode-badge fail">!</text>}
          </g>
        );
      })}
    </svg>
  );
}
