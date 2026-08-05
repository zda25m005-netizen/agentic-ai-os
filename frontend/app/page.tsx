"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

type Citation = { marker: number; source: string; score: number };
type AskResult = { answer: string; citations: Citation[]; sources: { source: string }[] };

type Step = { id: number; description: string; agent: string; status: string };
type Metrics = {
  spans: number;
  total_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  est_cost_usd: number;
};
type AgentResult = { answer: string; steps: Step[]; trace: string[]; metrics: Metrics };

function FeedbackButtons({ query, answer }: { query: string; answer: string }) {
  const [sent, setSent] = useState<string | null>(null);
  const [showBetter, setShowBetter] = useState(false);
  const [better, setBetter] = useState("");

  async function send(rating: "up" | "down", betterAnswer?: string) {
    try {
      await fetch(`${API}/feedback`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ query, answer, rating, better_answer: betterAnswer || null }),
      });
      setSent(rating === "up" ? "Thanks for the feedback 👍" : "Thanks — noted 👎");
      setShowBetter(false);
    } catch {
      setSent("Could not send feedback");
    }
  }

  if (sent) return <div className="feedback-done">{sent}</div>;

  return (
    <div className="feedback">
      <button className="fb" onClick={() => send("up")}>👍 Helpful</button>
      <button className="fb" onClick={() => setShowBetter((v) => !v)}>👎 Needs work</button>
      {showBetter && (
        <div className="feedback-better">
          <textarea
            placeholder="Optional: what would a better answer be?"
            value={better}
            onChange={(e) => setBetter(e.target.value)}
          />
          <button className="fb" onClick={() => send("down", better)}>Submit</button>
        </div>
      )}
    </div>
  );
}

export default function Home() {
  const [mode, setMode] = useState<"agent" | "ask">("agent");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [ask, setAsk] = useState<AskResult | null>(null);
  const [agent, setAgent] = useState<AgentResult | null>(null);
  const [lastQuery, setLastQuery] = useState("");

  async function run() {
    if (!input.trim() || loading) return;
    setLoading(true);
    setError("");
    setAsk(null);
    setAgent(null);
    try {
      if (mode === "ask") {
        const r = await fetch(`${API}/ask`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ question: input }),
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        setAsk(await r.json());
        setLastQuery(input);
      } else {
        const r = await fetch(`${API}/agent`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ goal: input }),
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        setAgent(await r.json());
        setLastQuery(input);
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "request failed";
      setError(`${msg} — is the API running on ${API}?`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="wrap">
      <h1>Agentic AI OS</h1>
      <p className="sub">Hybrid RAG + multi-agent orchestrator with tools, memory, and cost tracking.</p>

      <div className="tabs">
        <div className={`tab ${mode === "agent" ? "active" : ""}`} onClick={() => setMode("agent")}>
          Agent
        </div>
        <div className={`tab ${mode === "ask" ? "active" : ""}`} onClick={() => setMode("ask")}>
          Ask (RAG)
        </div>
      </div>

      <div className="inputrow">
        <input
          type="text"
          value={input}
          placeholder={mode === "agent" ? "Give the agent a goal…" : "Ask a question over your documents…"}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
        />
        <button className="send" onClick={run} disabled={loading}>
          {loading ? "Running…" : "Run"}
        </button>
      </div>

      {error && <div className="card error">{error}</div>}

      {ask && (
        <>
          <div className="card">
            <h3>Answer</h3>
            <div className="answer">{ask.answer}</div>
            <FeedbackButtons query={lastQuery} answer={ask.answer} />
          </div>
          {ask.citations?.length > 0 && (
            <div className="card">
              <h3>Citations</h3>
              <div className="chips">
                {ask.citations.map((c) => (
                  <span key={c.marker} className="chip ok">
                    [{c.marker}] {c.source} · {c.score.toFixed(2)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {agent && (
        <>
          <div className="card">
            <h3>Answer</h3>
            <div className="answer">{agent.answer}</div>
            <FeedbackButtons query={lastQuery} answer={agent.answer} />
          </div>
          {agent.steps?.length > 0 && (
            <div className="card">
              <h3>Plan</h3>
              <div className="chips">
                {agent.steps.map((s) => (
                  <span key={s.id} className={`chip ${s.status === "done" ? "ok" : ""}`}>
                    {s.agent}: {s.description}
                  </span>
                ))}
              </div>
            </div>
          )}
          <div className="card">
            <h3>Execution trace</h3>
            <div className="trace">
              {agent.trace.map((t, i) => (
                <div key={i}>{t}</div>
              ))}
            </div>
          </div>
          <div className="card">
            <h3>Run metrics</h3>
            <div className="metrics">
              <div className="metric">
                <b>{(agent.metrics.total_ms / 1000).toFixed(1)}s</b>
                <span>latency</span>
              </div>
              <div className="metric">
                <b>{agent.metrics.prompt_tokens + agent.metrics.completion_tokens}</b>
                <span>tokens</span>
              </div>
              <div className="metric">
                <b>${agent.metrics.est_cost_usd.toFixed(6)}</b>
                <span>est. cost</span>
              </div>
              <div className="metric">
                <b>{agent.metrics.spans}</b>
                <span>spans</span>
              </div>
            </div>
          </div>
        </>
      )}

      {!ask && !agent && !error && (
        <p className="hint">Start the API with <code>make run</code>, then try a goal like “What is 128 * 47? Use a tool.”</p>
      )}
    </main>
  );
}
