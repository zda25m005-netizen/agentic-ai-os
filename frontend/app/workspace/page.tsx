"use client";

import { useEffect, useMemo, useState } from "react";
import AgentGraph from "../components/AgentGraph";
import {
  FINAL_ANSWER,
  LiveState,
  NodeState,
  STEPS,
} from "../lib/demo";

const SPEEDS = [1, 2, 4];
const BASE_MS = 1100;

const EMPTY_LIVE: LiveState = {
  agent: "—", step: "Idle", progress: "0 / 6", tool: "—",
  memoryHits: 0, docs: 0, tokens: 0, cost: 0, latency: 0,
};

export default function Workspace() {
  const [i, setI] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);

  useEffect(() => {
    if (!playing || i >= STEPS.length - 1) return;
    const t = setTimeout(() => setI((n) => Math.min(n + 1, STEPS.length - 1)), BASE_MS / speed);
    return () => clearTimeout(t);
  }, [i, playing, speed]);

  // cumulative node states + live state up to the current step
  const { states, live, done } = useMemo(() => {
    const s: Record<string, NodeState> = {};
    let l: LiveState = { ...EMPTY_LIVE };
    for (let k = 0; k <= i; k++) {
      Object.assign(s, STEPS[k].states);
      l = { ...l, ...STEPS[k].live };
    }
    return { states: s, live: l, done: i >= STEPS.length - 1 };
  }, [i]);

  const trace = STEPS.slice(0, i + 1).map((s) => s.trace);
  const activeEdge = STEPS[i].activeEdge;
  const restart = () => { setI(0); setPlaying(true); };

  return (
    <div className="ws">
      <div className="ws-head">
        <div>
          <div className="ws-crumb"><span className="demo-badge">DEMO MODE</span> deterministic mock run</div>
          <h1 className="ws-title">Compare NVIDIA, AMD and Intel AI strategy</h1>
        </div>
        <div className="ws-metrics">
          <div className="ws-metric"><b>{live.tokens.toLocaleString()}</b><span>tokens</span></div>
          <div className="ws-metric"><b>${live.cost.toFixed(4)}</b><span>cost</span></div>
          <div className="ws-metric"><b>{live.latency.toFixed(2)}s</b><span>latency</span></div>
          <div className="ws-metric"><b>{done ? (states.result === "done" ? "✓" : "—") : "●"}</b><span>status</span></div>
        </div>
      </div>

      <div className="ws-controls">
        <button className="btn btn-primary" onClick={() => setPlaying((p) => !p)}>{playing ? "❚❚ Pause" : "▶ Play"}</button>
        <button className="btn" onClick={restart}>↻ Replay</button>
        {SPEEDS.map((s) => (
          <button key={s} className={`btn chipbtn ${speed === s ? "active" : ""}`} onClick={() => setSpeed(s)}>{s}x</button>
        ))}
        <div className="ws-progress"><div className="bar"><span style={{ width: `${(i / (STEPS.length - 1)) * 100}%` }} /></div></div>
      </div>

      <div className="ws-grid">
        <div className="card ws-graphcard">
          <h3>Agent execution graph</h3>
          <AgentGraph states={states} activeEdge={activeEdge} />
        </div>

        <div className="card ws-live">
          <h3>Live state</h3>
          <dl className="live-list">
            <dt>Agent</dt><dd>{live.agent}</dd>
            <dt>Step</dt><dd>{live.step}</dd>
            <dt>Progress</dt><dd>{live.progress}</dd>
            <dt>Tool</dt><dd>{live.tool}</dd>
            <dt>Memory hits</dt><dd>{live.memoryHits}</dd>
            <dt>Docs</dt><dd>{live.docs}</dd>
            <dt>Tokens</dt><dd className="mono">{live.tokens.toLocaleString()}</dd>
            <dt>Cost</dt><dd className="mono">${live.cost.toFixed(4)}</dd>
            <dt>Latency</dt><dd className="mono">{live.latency.toFixed(2)}s</dd>
          </dl>
        </div>
      </div>

      {done && states.result === "done" && (
        <div className="card ws-result">
          <h3>✓ Mission completed — final answer</h3>
          <p>{FINAL_ANSWER}</p>
        </div>
      )}

      <div className="card ws-trace">
        <h3>Execution trace</h3>
        <div className="trace-list">
          {trace.map((e, k) => (
            <div key={k} className={`trace-row status-${e.status}`}>
              <span className="mono t-ts">{e.t}</span>
              <span className="t-comp">{e.comp}</span>
              <span className="t-ev">{e.ev}</span>
              <span className="mono t-tok">{e.tokens}t</span>
              <span className="mono t-cost">${e.cost.toFixed(4)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
