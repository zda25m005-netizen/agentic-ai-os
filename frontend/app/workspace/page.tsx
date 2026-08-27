"use client";

import { useEffect, useMemo, useState } from "react";
import AgentGraph from "../components/AgentGraph";
import {
  CONVERSATION,
  FINAL_ANSWER,
  LiveState,
  NodeState,
  ROLE_COLOR,
  STEPS,
  TOOL_CALLS,
} from "../lib/demo";

const BASE_MS = 1100;
const SPEEDS = [1, 2, 4];
const EMPTY_LIVE: LiveState = { agent: "—", step: "Idle", progress: "0 / 6", tool: "—", memoryHits: 0, docs: 0, tokens: 0, cost: 0, latency: 0 };
const PIPE = [
  { name: "Planning", color: "#a855f7" },
  { name: "Research", color: "#2196ff" },
  { name: "Analysis", color: "#18d5d1" },
  { name: "Critic", color: "#f5b82e" },
  { name: "Finalize", color: "#18d889" },
];

function fmt(s: number) {
  const m = Math.floor(s / 60), sec = Math.floor(s % 60);
  return `00:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

// deterministic pseudo-resource value that drifts with the step
function res(i: number, seed: number) {
  return 25 + Math.round((Math.sin(i * 0.9 + seed) * 0.5 + 0.5) * 55);
}

function Ring({ value, color, label }: { value: number; color: string; label: string }) {
  const r = 22, c = 2 * Math.PI * r;
  return (
    <div className="ring">
      <svg width="58" height="58" viewBox="0 0 58 58">
        <circle cx="29" cy="29" r={r} className="ring-bg" />
        <circle cx="29" cy="29" r={r} stroke={color} strokeWidth="4" fill="none"
          strokeDasharray={c} strokeDashoffset={c - (value / 100) * c} strokeLinecap="round"
          transform="rotate(-90 29 29)" style={{ transition: "stroke-dashoffset .6s ease" }} />
        <text x="29" y="33" textAnchor="middle" className="ring-val">{value}%</text>
      </svg>
      <span style={{ color }}>{label}</span>
    </div>
  );
}

function Spark({ data, color }: { data: number[]; color: string }) {
  const w = 68, h = 22, max = Math.max(...data, 1);
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - (v / max) * h}`).join(" ");
  return <svg width={w} height={h} className="spark"><polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" /></svg>;
}

export default function Workspace() {
  const [i, setI] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);

  useEffect(() => {
    if (!playing || i >= STEPS.length - 1) return;
    const t = setTimeout(() => setI((n) => Math.min(n + 1, STEPS.length - 1)), BASE_MS / speed);
    return () => clearTimeout(t);
  }, [i, playing, speed]);

  const { states, live, done } = useMemo(() => {
    const s: Record<string, NodeState> = {};
    let l: LiveState = { ...EMPTY_LIVE };
    for (let k = 0; k <= i; k++) { Object.assign(s, STEPS[k].states); l = { ...l, ...STEPS[k].live }; }
    return { states: s, live: l, done: i >= STEPS.length - 1 };
  }, [i]);

  const events = [...STEPS.slice(0, i + 1).map((s) => s.trace)].reverse();
  const activeEdge = STEPS[i].activeEdge;
  const convo = CONVERSATION.filter((c) => c.at <= i);
  const tokenHist = STEPS.slice(0, i + 1).map((s) => s.live.tokens ?? 0);
  const pct = Math.round((i / (STEPS.length - 1)) * 100);
  // pipeline stage state
  const stageState = (idx: number): string => {
    const stageStart = [1, 3, 6, 7, 11]; // step at which each stage becomes active
    if (done) return "done";
    if (i >= (stageStart[idx + 1] ?? 99)) return "done";
    if (i >= stageStart[idx]) return "active";
    return "pending";
  };
  const statusWord = done ? "COMPLETED" : "LIVE";

  return (
    <div className="cp">
      {/* header */}
      <div className="cp-head">
        <div>
          <div className="cp-crumb">Missions / <span className="demo-badge">DEMO</span></div>
          <h1 className="cp-title">Compare NVIDIA, AMD and Intel AI strategy</h1>
          <div className="cp-sub">Priority <b style={{ color: "#f5b82e" }}>High</b> · created just now · scripted demo run</div>
        </div>
        <div className="cp-head-actions">
          <span className={`live-pill ${done ? "completed" : "on"}`}><i /> {statusWord}</span>
          <span className="cp-timer mono">{fmt(live.latency)}</span>
          <button className="cp-btn" onClick={() => setPlaying((p) => !p)}>{playing ? "❚❚" : "▶"}</button>
          <button className="cp-btn" onClick={() => { setI(0); setPlaying(true); }}>↻ Replay</button>
          {SPEEDS.map((s) => <button key={s} className={`cp-btn ${speed === s ? "on" : ""}`} onClick={() => setSpeed(s)}>{s}x</button>)}
        </div>
      </div>

      {/* pipeline */}
      <div className="cp-pipeline">
        {PIPE.map((p, idx) => {
          const st = stageState(idx);
          return (
            <div key={p.name} className={`cps cps-${st}`}>
              <span className="cps-dot" style={{ ["--c" as string]: p.color }}><i /></span>
              <div><b style={{ color: st === "pending" ? undefined : p.color }}>{p.name}</b><span>{st}</span></div>
              {idx < PIPE.length - 1 && <div className={`cps-conn ${st === "done" ? "on" : st === "active" ? "live" : ""}`} />}
            </div>
          );
        })}
      </div>

      {/* main 3-col */}
      <div className="cp-main">
        {/* graph */}
        <div className="cp-panel cp-graph">
          <div className="cp-panel-h">TASK GRAPH <span className="mono cp-zoom">100%</span></div>
          <div className="cp-graph-grid">
            <AgentGraph states={states} activeEdge={activeEdge} />
          </div>
        </div>

        {/* middle column */}
        <div className="cp-col">
          <div className="cp-panel">
            <div className="cp-panel-h">LIVE ACTIVITY</div>
            <div className="waveform">{Array.from({ length: 34 }).map((_, k) => (
              <span key={k} style={{ animationDelay: `${(k % 7) * 90}ms`, background: k % 3 === 0 ? "#a855f7" : k % 3 === 1 ? "#2196ff" : "#18d5d1" }} />
            ))}</div>
            <div className="act-mini">
              {events.slice(0, 4).map((e, k) => (
                <div key={k} className="act-mini-row"><span className="mono">{e.t.slice(0, 5)}</span><span style={{ color: "#18d5d1" }}>{e.comp}</span><span className="muted">{e.ev}</span></div>
              ))}
            </div>
          </div>

          <div className="cp-panel">
            <div className="cp-panel-h">MISSION METRICS</div>
            <div className="cp-metrics">
              <div className="cp-metric"><span>Tokens</span><b>{live.tokens.toLocaleString()}</b><Spark data={tokenHist} color="#2196ff" /></div>
              <div className="cp-metric"><span>Cost</span><b>${live.cost.toFixed(4)}</b><Spark data={tokenHist.map((t) => t * 0.4)} color="#a855f7" /></div>
              <div className="cp-metric"><span>Latency</span><b>{live.latency.toFixed(1)}s</b><Spark data={[3, 4, 3, 5, 4, live.latency]} color="#18d5d1" /></div>
              <div className="cp-metric"><span>Success</span><b>{done ? 96 : 88 + i}%</b><Spark data={[80, 84, 86, 88, 92, done ? 96 : 90]} color="#18d889" /></div>
            </div>
          </div>

          <div className="cp-panel">
            <div className="cp-panel-h">RESOURCE USAGE</div>
            <div className="cp-rings">
              <Ring value={res(i, 0)} color="#a855f7" label="CPU" />
              <Ring value={res(i, 2)} color="#2196ff" label="MEM" />
              <Ring value={res(i, 4)} color="#18d5d1" label="GPU" />
              <Ring value={res(i, 6)} color="#f5b82e" label="NET" />
            </div>
          </div>
        </div>

        {/* event stream + token stream */}
        <div className="cp-col cp-events">
          <div className="cp-panel cp-eventstream">
            <div className="cp-tabs"><span className="on">EVENT STREAM</span><span>TRACE</span><span>LOGS</span></div>
            <div className="timeline">
              {events.map((e, k) => (
                <div key={k} className="tl-row" style={{ animation: k === 0 ? "actIn .35s ease" : undefined }}>
                  <span className={`tl-dot ${e.status}`} />
                  <div><div className="tl-top"><span className="mono tl-t">{e.t}</span></div>
                    <div className="tl-comp" style={{ color: "#18d5d1" }}>{e.comp}</div>
                    <div className="tl-ev muted">{e.ev}</div></div>
                </div>
              ))}
            </div>
          </div>

          <div className="cp-panel">
            <div className="cp-panel-h">TOKEN STREAM<span className="cp-panel-sub">live token generation</span></div>
            <svg className="tokenstream" viewBox="0 0 260 70" preserveAspectRatio="none">
              {["#a855f7", "#2196ff", "#18d5d1"].map((c, k) => (
                <path key={c} className={`tw tw${k}`} stroke={c} fill="none" strokeWidth="1.6"
                  d="M0,35 C40,10 60,60 100,35 C140,10 160,60 200,35 C240,10 260,50 300,35" />
              ))}
            </svg>
            <div className="tok-counts">
              <div><span>Input</span><b className="mono">{Math.round(live.tokens * 0.2).toLocaleString()}</b></div>
              <div><span>Output</span><b className="mono">{Math.round(live.tokens * 0.8).toLocaleString()}</b></div>
              <div><span>Total</span><b className="mono">{live.tokens.toLocaleString()}</b></div>
            </div>
          </div>
        </div>
      </div>

      {/* bottom telemetry */}
      <div className="cp-bottom">
        <div className="cp-panel">
          <div className="cp-panel-h">AGENT CONVERSATION <span className="live-mini">● LIVE</span></div>
          <div className="convo">
            {convo.map((c, k) => (
              <div key={k} className="convo-row"><b style={{ color: ROLE_COLOR[c.role] }}>{c.role}:</b> <span>{c.text}</span></div>
            ))}
            {convo.length === 0 && <span className="muted">waiting…</span>}
          </div>
        </div>

        <div className="cp-panel">
          <div className="cp-panel-h">CURRENT STEP</div>
          <div className="step-agent" style={{ color: "#18d5d1" }}>{live.agent} <span className="muted" style={{ fontSize: 12 }}>{done ? "done" : "running"}</span></div>
          <div className="muted" style={{ fontSize: 13, margin: "6px 0 10px" }}>{live.step}</div>
          <div className="progress"><div className="bar"><span className="bar-anim" style={{ width: `${done ? 100 : 40 + i * 5}%` }} /></div><small>{live.progress}</small></div>
          <div className="step-grid">
            <div><span>Tokens</span><b className="mono">{live.tokens.toLocaleString()}</b></div>
            <div><span>Cost</span><b className="mono">${live.cost.toFixed(4)}</b></div>
          </div>
        </div>

        <div className="cp-panel">
          <div className="cp-panel-h">TOOL CALLS</div>
          <div className="toolcalls">
            {TOOL_CALLS.map((t) => {
              const ok = i >= t.doneAt;
              return (
                <div key={t.name} className="tc-row">
                  <div><b>{t.name}</b><span className="muted">{t.desc}</span></div>
                  <div className="tc-right"><span className="mono muted">{t.latency}</span>
                    <span className={`tc-status ${ok ? "ok" : "run"}`}>{ok ? "✓" : "●"}</span></div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="cp-panel cp-qa">
          <div className="cp-panel-h">QUICK ACTIONS</div>
          <button className="cp-action" onClick={() => setPlaying(false)}>❚❚ Pause mission</button>
          <button className="cp-action" onClick={() => { setI(0); setPlaying(true); }}>⧉ Clone mission</button>
          <button className="cp-action">⤓ Export results</button>
          <button className="cp-action danger">🗑 Delete mission</button>
        </div>
      </div>

      {done && (
        <div className="cp-panel cp-final">
          <div className="cp-panel-h" style={{ color: "#18d889" }}>✓ MISSION COMPLETED — FINAL ANSWER</div>
          <p style={{ margin: 0, lineHeight: 1.6 }}>{FINAL_ANSWER}</p>
        </div>
      )}
    </div>
  );
}
